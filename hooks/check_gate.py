#!/usr/bin/env python3
"""check_gate.py -- Block git commits without merged reviewer consensus.
Event: PreToolUse
Matcher: Bash
If: Bash(git commit *)

Rule 17 exception: full rewrite justified -- legacy code reads approvals_dir which is
fundamentally incompatible with the merged_verdicts contract (D2 single writer).
Surgical edit would preserve dead paths. New file is simpler than original.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import time as _time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.common import current_task_id, hook_input, load_project_config, read_json, resolve_path, resolve_project_root, trace_hook


def _is_plain_git_commit(command: str) -> bool:
    """Return True only for plain `git commit` — not compound commands."""
    import shlex
    if any(c in command for c in ("&&", ";", "|")):
        return False
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] == "git" and parts[1] == "commit"


def _deny(reason: str):
    print(json.dumps({"decision": "deny", "reason": reason}))
    print(reason, file=sys.stderr)
    sys.exit(2)


def main():
    _t0 = _time.monotonic()
    # P3: opt-in -- inert without agent identity
    agent = os.environ.get("GATE_AGENT_NAME", "").strip()
    if not agent:
        trace_hook(hook="check_gate", agent="", decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="no agent")
        return  # exit 0 = allow

    from lib.common import is_hook_disabled
    if is_hook_disabled("check_gate"):
        trace_hook(hook="check_gate", agent=agent, decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="hook disabled")
        return  # exit 0 = allow (disabled hook is transparent)

    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        trace_hook(hook="check_gate", agent=agent, decision="deny",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="malformed stdin")
        _deny("check-gate: malformed hook payload")

    tool_name, tool_input, _, _ = hook_input(data)
    if tool_name != "Bash":
        trace_hook(hook="check_gate", agent=agent, decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   tool=tool_name, reason="tool not bash")
        return
    command = str(tool_input.get("command", ""))
    if not _is_plain_git_commit(command):
        trace_hook(hook="check_gate", agent=agent, decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   tool=tool_name, command=command, reason="not plain git commit")
        return

    try:
        project_root = resolve_project_root()
        config = load_project_config(project_root)
    except Exception as exc:
        _deny(f"check-gate: cannot load project config -- {exc}")
        return

    # Protected branch check -- commits to non-protected branches pass freely
    protected = config.get("gate", {}).get("protected_branches", [])
    if protected:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(project_root),
            )
            current_branch = result.stdout.strip()
        except Exception:
            current_branch = ""
        # "HEAD" = detached HEAD state -- treat as protected (require verdict check)
        if current_branch and current_branch != "HEAD" and current_branch not in protected:
            trace_hook(hook="check_gate", agent=agent, decision="allow",
                       elapsed_ms=(_time.monotonic() - _t0) * 1000,
                       project_root=project_root, config=config,
                       reason="non-protected branch")
            return  # non-protected branch -- allow freely

    # Resolve current task ID
    try:
        current_task_file = resolve_path("current_task", project_root, config)
        current_task = read_json(current_task_file, {})
    except Exception:
        current_task = {}

    task_id = current_task_id(current_task)
    if not task_id:
        trace_hook(hook="check_gate", agent=agent, decision="deny",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="no task_id")
        _deny("check-gate: no current task ID -- cannot verify reviewer consensus")
        return

    # Read merged verdict written by watcher (D2)
    try:
        merged_verdicts_dir = resolve_path("merged_verdicts", project_root, config)
        verdict_file = merged_verdicts_dir / f"{task_id}.json"
        verdict = read_json(verdict_file, None)
    except Exception:
        verdict = None

    if verdict is None:
        trace_hook(hook="check_gate", agent=agent, decision="deny",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="no verdict file", task_id=task_id)
        _deny(
            f"check-gate: no merged verdict for task {task_id} -- "
            f"reviewers have not yet reached consensus. "
            f"Wait for watcher to write {task_id}.json to merged_verdicts/."
        )
        return

    # D2 normalizes verdicts to "approved"/"rejected" — no need for full approve_words set
    if str(verdict.get("verdict", "")).lower() == "approved":
        trace_hook(hook="check_gate", agent=agent, decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="approved", task_id=task_id)
        return  # consensus approved -- allow commit

    reason = verdict.get("reason", "rejected by reviewer consensus")
    dissent = verdict.get("dissent", [])
    dissent_str = f" Dissenters: {', '.join(dissent)}." if dissent else ""
    trace_hook(hook="check_gate", agent=agent, decision="deny",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               reason="rejected", task_id=task_id, dissent=dissent)
    _deny(f"check-gate: task {task_id} not approved -- {reason}.{dissent_str}")
    return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("BLOCKED: check-gate error -- blocked for safety", file=sys.stderr)
        sys.exit(2)
