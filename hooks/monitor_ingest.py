#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

"""
Monitor ingest — PostToolUse hook.

Source: MASTER_SPECS_MERGED.md
  - "Wake + injection mechanism (the core loop)"
  - Components #4: coder PostToolUse writes JSON summary to monitor inbox.
  - Watcher COPY/MERGE/DISTRIBUTE/LIVENESS — ingest wakes monitor via watcher pulse.

Behavior:
  - Fires on every tool call from a coder-role agent.
  - Skips silently for non-coder agents (matcher can't be role-aware).
  - Writes a JSON summary of the tool call to each routing.cc_all target's
    inbox (dispatch/<cc>/inbox/).
  - Truncates tool_input and tool_response to keep injection bloat bounded.
  - Never blocks the coder's tool call — always returns {}, always exits 0,
  - Never raises — errors log to stderr.

Relationship to activity_logger.py: activity_logger writes an audit log line
per tool call AND optionally ships to monitor via send.py. monitor_ingest is
the cleaner dedicated path — same data, direct write to monitor inbox, no
subprocess hop. Both can run; activity_logger's subprocess shipping becomes
redundant and should be disabled via session.monitor_activity_to_dispatch=false
when monitor_ingest is wired.
"""
import json
import os
import time as _time

from lib.common import (
    atomic_write,
    file_stamp,
    hook_input,
    load_project_config,
    resolve_path,
    resolve_project_root,
    timestamp,
    trace_hook,
)


OK = {}
MAX_INPUT_SUMMARY = 500
MAX_RESPONSE_SUMMARY = 500
COMMAND_MATCHER_TOOLS = {"Bash", "Write", "Edit", "MultiEdit", "Read", "Grep", "Glob"}


def _log_stderr(msg: str) -> None:
    try:
        print(f"[monitor_ingest] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _truncate(value, limit: int) -> str:
    """JSON-serialize then truncate to bound injection bloat."""
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(value)
    if len(s) > limit:
        return s[:limit] + f"...[+{len(s) - limit}]"
    return s


def _agent_has_role(config: dict, agent_name: str, role: str) -> bool:
    for a in config.get("agents", []):
        if a.get("name") == agent_name:
            return role in (a.get("roles") or [])
    return False


def main() -> int:
    agent = os.environ.get("GATE_AGENT_NAME", "").strip()
    if not agent:
        print(json.dumps(OK))
        return 0

    from lib.common import is_hook_disabled
    if is_hook_disabled("monitor_ingest"):
        print(json.dumps(OK))
        return 0

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        print(json.dumps(OK))
        return 0

    _t0 = _time.monotonic()

    tool_name, tool_input, tool_response, exit_code = hook_input(payload)
    if tool_name not in COMMAND_MATCHER_TOOLS:
        trace_hook(hook="monitor_ingest", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="tool not matched")
        print(json.dumps(OK))
        return 0

    try:
        project_root = resolve_project_root()
        config = load_project_config(project_root)
        dispatch_root = resolve_path("dispatch_root", project_root, config)
    except Exception as exc:
        _log_stderr(f"config load failed: {exc}")
        print(json.dumps(OK))
        return 0

    # Only coders ship to monitor inbox.
    if not _agent_has_role(config, agent, "coder"):
        trace_hook(hook="monitor_ingest", agent=agent, decision="skip",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="not coder")
        print(json.dumps(OK))
        return 0

    cc_all = config.get("routing", {}).get("cc_all", [])
    if not cc_all:
        trace_hook(hook="monitor_ingest", agent=agent, decision="skip",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="no cc_all")
        print(json.dumps(OK))
        return 0

    summary = {
        "ts": timestamp(config),
        "from": agent,
        "tool": tool_name,
        "exit_code": exit_code,
        "tool_input_summary": _truncate(tool_input, MAX_INPUT_SUMMARY),
        "tool_response_summary": _truncate(tool_response, MAX_RESPONSE_SUMMARY),
    }
    body = json.dumps(summary, ensure_ascii=False, indent=2)

    fs = file_stamp(config)
    safe_tool = tool_name.replace("/", "_").replace("\\", "_")
    filename = f"{fs}-{agent}-{safe_tool}.json"

    for recipient in cc_all:
        if recipient == agent:
            continue
        inbox = dispatch_root / recipient / "inbox"
        try:
            inbox.mkdir(parents=True, exist_ok=True)
            atomic_write(inbox / filename, body)
        except OSError as exc:
            _log_stderr(f"write to {recipient}/inbox failed: {exc}")

    trace_hook(hook="monitor_ingest", agent=agent, decision="allow",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               tool=tool_name, recipients=cc_all)
    print(json.dumps(OK))
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # P4: advisory — fail-open
