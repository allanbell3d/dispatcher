#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import os
import re
import time as _time

from lib.common import hook_input, load_project_config, read_json, resolve_path, resolve_project_root, write_json, trace_hook

TASK_TAG_RE = re.compile(r"\[task:([A-Za-z0-9._-]+)\]|task:([A-Za-z0-9._-]+)", re.I)

def archive_approvals(approvals_dir: Path, task_id: str):
    archive_dir = approvals_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in approvals_dir.glob(f"{task_id}-*.json"):
        target = archive_dir / path.name
        if target.exists():
            target = archive_dir / f"{path.stem}-used{path.suffix}"
        path.replace(target)

def main() -> int:
    if not os.environ.get('GATE_AGENT_NAME', '').strip():
        sys.exit(0)
    agent = os.environ.get("GATE_AGENT_NAME", "").strip()

    from lib.common import is_hook_disabled
    if is_hook_disabled("dispatch_next_bug"):
        sys.exit(0)

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        print(json.dumps({}))
        return 0

    _t0 = _time.monotonic()

    tool_name, tool_input, _, exit_code = hook_input(payload)
    command = str(tool_input.get("command", ""))
    if tool_name != "Bash" or "git commit" not in command or exit_code != 0:
        trace_hook(hook="dispatch_next_bug", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="not a successful git commit")
        print(json.dumps({}))
        return 0

    project_root = resolve_project_root()
    config = load_project_config(project_root)
    current_task_file = resolve_path("current_task", project_root, config)
    tasks_file = resolve_path("tasks_file", project_root, config)
    approvals_dir = resolve_path("approvals", project_root, config)
    current = read_json(current_task_file, {})
    task_id = current.get("id")
    if not task_id:
        trace_hook(hook="dispatch_next_bug", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="no current task_id")
        print(json.dumps({}))
        return 0

    match = TASK_TAG_RE.search(command)
    commit_task = next((g for g in match.groups() if g), "") if match else ""
    if commit_task != task_id:
        trace_hook(hook="dispatch_next_bug", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="commit task mismatch", commit_task=commit_task, current_task=task_id)
        print(json.dumps({}))
        return 0

    tasks = read_json(tasks_file, [])
    if not isinstance(tasks, list):
        trace_hook(hook="dispatch_next_bug", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="tasks not a list")
        print(json.dumps({}))
        return 0

    next_task = None
    current_batch = current.get("batch")
    for item in tasks:
        if item.get("id") == task_id:
            item["status"] = "done"
    for item in tasks:
        if item.get("status") == "pending":
            next_task = item
            break

    archive_approvals(approvals_dir, task_id)
    write_json(tasks_file, tasks)

    if next_task:
        next_task = dict(next_task)
        next_task["status"] = "in_progress"
        for item in tasks:
            if item.get("id") == next_task.get("id"):
                item["status"] = "in_progress"
        write_json(tasks_file, tasks)
        write_json(current_task_file, next_task)
        additional = (
            f"TASK COMPLETE: {task_id}\n"
            f"NEXT TASK: {next_task.get('id')} -- {next_task.get('title')}\n"
            f"FILE: {next_task.get('file','')}\n"
            f"DETAILS: {next_task.get('details','')}\n"
        )
        if config.get("session", {}).get("halt_between_batches") and current_batch and next_task.get("batch") != current_batch:
            additional += "\nBATCH BOUNDARY: stop and wait for Allan before continuing."
        trace_hook(hook="dispatch_next_bug", agent=agent,
                   decision="advance", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   completed=task_id, next=next_task.get("id"))
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": additional}}))
    else:
        trace_hook(hook="dispatch_next_bug", agent=agent,
                   decision="advance", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   completed=task_id, next=None)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": f"ALL TASKS COMPLETE after {task_id}.\n"}}))
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # P4: advisory — fail-open
