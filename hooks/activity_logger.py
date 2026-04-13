#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import os
import re
import subprocess
import time as _time

from lib.common import hook_input, load_project_config, log_line, resolve_path, resolve_project_root, resolve_shared_roots, timestamp, trace_hook

SECRET_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"), "Bearer ***REDACTED***"),
    (re.compile(r"sk-[A-Za-z0-9]{10,}"), "sk-***REDACTED***"),
    (re.compile(r"rt_[A-Za-z0-9\-]{10,}"), "rt_***REDACTED***"),
]

def redact(text: str) -> str:
    for pattern, repl in SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text

def main() -> int:
    if not os.environ.get('GATE_AGENT_NAME', '').strip():
        sys.exit(0)

    from lib.common import is_hook_disabled
    if is_hook_disabled("activity_logger"):
        sys.exit(0)

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    _t0 = _time.monotonic()

    if payload.get("agent_id"):
        return 0

    project_root = resolve_project_root()
    config = load_project_config(project_root)
    logs_dir = resolve_path("logs", project_root, config)
    orch_root, _ = resolve_shared_roots(config)
    agent = os.environ.get("GATE_AGENT_NAME", "unknown").strip() or "unknown"

    tool_name, tool_input, tool_response, exit_code = hook_input(payload)
    summary = {
        "at": timestamp(config),
        "agent": agent,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_response": tool_response,
        "exit_code": exit_code,
    }
    raw = redact(json.dumps(summary, ensure_ascii=False))
    log_line(logs_dir / f"activity_{agent}.log", raw)

    cc_all = config.get("routing", {}).get("cc_all", [])
    if config.get("session", {}).get("monitor_activity_to_dispatch") and agent not in cc_all and tool_name in {"Bash", "Write", "Edit", "MultiEdit"}:
        send_py = orch_root / "scripts" / "send.py"
        for recipient in cc_all:
            if recipient == agent:
                continue
            try:
                subprocess.run(
                    [sys.executable, str(send_py), "--project", str(project_root), "--activity", recipient],
                    input=json.dumps(summary),
                    text=True,
                    capture_output=True,
                    timeout=5,
                    env={**os.environ, "GATE_AGENT_NAME": agent},
                )
            except Exception:
                pass

    trace_hook(hook="activity_logger", agent=agent, decision="allow",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               tool=tool_name)
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # P4: advisory — fail-open
