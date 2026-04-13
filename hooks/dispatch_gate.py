#!/usr/bin/env python3
"""dispatch_gate.py — Block gated agents from writing when no task dispatched.
Event: PreToolUse
Matcher: Write|Edit|MultiEdit|Bash|Glob|Grep|ListDir
"""
from pathlib import Path
import json
import os
import sys
import time as _time
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.common import audit_log, hook_input, is_halted, load_project_config, read_json, resolve_path, resolve_project_root, strip_gate_prefix, trace_hook

GATED_TOOLS = {"Write", "Edit", "MultiEdit", "Bash", "Glob", "Grep", "ListDir"}


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
    print(json.dumps({"error": reason}))
    print(reason, file=sys.stderr)
    sys.exit(2)


def main():
    # P3: opt-in — inert without agent identity
    agent = os.environ.get("GATE_AGENT_NAME", "").strip()
    if not agent:
        return  # exit 0 = allow

    # Runtime toggle: if disabled via flag file, allow transparently
    from lib.common import is_hook_disabled
    if is_hook_disabled("dispatch_gate"):
        return  # exit 0 = allow (disabled hook is transparent)

    # Read hook input from stdin
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input — allow (fail-open on parse, fail-secure in wrapper)

    _t0 = _time.monotonic()

    # Tool match — use hook_input() for key-name resilience (tool_name/tool)
    tool_name, tool_input, _, _ = hook_input(data)
    if tool_name not in GATED_TOOLS:
        return  # exit 0 = allow

    # Locate project root and load config
    try:
        project_root = resolve_project_root()
        config = load_project_config(project_root)
    except Exception as exc:
        _deny(f"dispatch-gate: cannot resolve project config — {exc}")

    # Resolve dispatch paths
    try:
        dispatch_root = resolve_path("dispatch_root", project_root, config)
    except Exception as exc:
        _deny(f"dispatch-gate: cannot resolve dispatch_root — {exc}")

    # Config agent names include the gate- prefix (e.g. "gate-ralph").
    # Dispatch dirs match config names: dispatch/gate-ralph/
    agent_dir = dispatch_root / agent
    ready_file = agent_dir / "ready"
    inbox_dir = agent_dir / "inbox"

    # --- State machine (flat if/elif, ordered) ---

    # BOOT: ready file absent — agent not yet initialised, allow freely
    if not ready_file.exists():
        trace_hook(hook="dispatch_gate", agent=agent, decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   state="BOOT", tool=tool_name)
        return  # exit 0 = allow

    # HALTED: halt flag set — block with stored reason
    halted, reason = is_halted(agent, project_root, config)
    if halted:
        audit_log("dispatch_gate", project_root=project_root, config=config,
                  agent=agent, state="HALTED", tool=tool_name, action="deny",
                  reason=reason)
        trace_hook(hook="dispatch_gate", agent=agent, decision="deny",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   state="HALTED", tool=tool_name, reason=reason)
        _deny(f"Agent '{agent}' is halted: {reason}")

    # DELIVERED: fan-in tracker active for this task + no merged verdict — allow only git commit
    # (Tracker-based detection avoids race: watcher archives outbox files within ~1s of processing)
    try:
        current_task_file = resolve_path("current_task", project_root, config)
        current_task = read_json(current_task_file, {})
    except Exception:
        current_task = {}

    task_id = (current_task.get("id") or current_task.get("task_id") or "").strip()

    if task_id:
        try:
            trackers_file = resolve_path("trackers", project_root, config)
            trackers_data = read_json(trackers_file, {})
            merged_verdicts_dir = resolve_path("merged_verdicts", project_root, config)
        except Exception:
            trackers_data = {}
            merged_verdicts_dir = None

        if merged_verdicts_dir is not None and task_id in trackers_data:
            verdict_file = merged_verdicts_dir / f"{task_id}.json"
            if not verdict_file.exists():
                command = str(tool_input.get("command", ""))
                if tool_name == "Bash" and _is_plain_git_commit(command):
                    audit_log("dispatch_gate", project_root=project_root, config=config,
                              agent=agent, state="DELIVERED", tool=tool_name, action="allow",
                              task_id=task_id)
                    trace_hook(hook="dispatch_gate", agent=agent, decision="allow",
                               elapsed_ms=(_time.monotonic() - _t0) * 1000,
                               project_root=project_root, config=config,
                               state="DELIVERED", tool=tool_name, task_id=task_id)
                    return  # exit 0 = allow
                audit_log("dispatch_gate", project_root=project_root, config=config,
                          agent=agent, state="DELIVERED", tool=tool_name, action="deny",
                          task_id=task_id)
                trace_hook(hook="dispatch_gate", agent=agent, decision="deny",
                           elapsed_ms=(_time.monotonic() - _t0) * 1000,
                           project_root=project_root, config=config,
                           state="DELIVERED", tool=tool_name, task_id=task_id)
                _deny(f"Agent '{agent}' is DELIVERED — awaiting reviewer consensus. Only 'git commit' is allowed.")

    # WORKING / WAITING: ready file exists — check inbox depth
    try:
        inbox_files = [
            p for p in inbox_dir.iterdir()
            if p.is_file() and p.suffix != ".tmp"
        ] if inbox_dir.is_dir() else []
    except OSError:
        inbox_files = []

    if inbox_files:
        # WORKING: task present in inbox — allow
        audit_log("dispatch_gate", project_root=project_root, config=config,
                  agent=agent, state="WORKING", tool=tool_name, action="allow",
                  inbox_depth=len(inbox_files))
        trace_hook(hook="dispatch_gate", agent=agent, decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   state="WORKING", tool=tool_name, inbox_depth=len(inbox_files))
        return  # exit 0 = allow

    # WAITING: ready file exists but inbox empty — block
    audit_log("dispatch_gate", project_root=project_root, config=config,
              agent=agent, state="WAITING", tool=tool_name, action="deny")
    trace_hook(hook="dispatch_gate", agent=agent, decision="deny",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               state="WAITING", tool=tool_name)
    _deny(f"Agent '{agent}' is WAITING: no task dispatched")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("BLOCKED: dispatch-gate error — blocked for safety", file=sys.stderr)
        sys.exit(2)
