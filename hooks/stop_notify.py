#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import subprocess
import time as _time

from lib.common import audit_log, load_project_config, resolve_project_root, resolve_shared_roots, trace_hook

def main() -> int:
    _t0 = _time.monotonic()
    if not os.environ.get('GATE_AGENT_NAME', '').strip():
        trace_hook(hook="stop_notify", agent="", decision="skip",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="no agent")
        sys.exit(0)

    from lib.common import is_hook_disabled
    if is_hook_disabled("stop_notify"):
        trace_hook(hook="stop_notify", agent=os.environ.get("GATE_AGENT_NAME", "").strip(),
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="hook disabled")
        sys.exit(0)

    project_root = resolve_project_root()
    config = load_project_config(project_root)
    orch_root, _ = resolve_shared_roots(config)
    send_py = orch_root / "scripts" / "send.py"
    agent = os.environ.get("GATE_AGENT_NAME", "unknown").strip() or "unknown"
    recipients = list(config.get("routing", {}).get("on_stop", []))
    failed = []
    for recipient in recipients:
        try:
            result = subprocess.run(
                [sys.executable, str(send_py), "--project", str(project_root), recipient, f"{agent} stopped unexpectedly", "--type", "stop_event"],
                text=True,
                capture_output=True,
                timeout=5,
                env={**os.environ, "GATE_AGENT_NAME": agent},
            )
            if result.returncode != 0:
                failed.append(recipient)
                audit_log("stop_notify_failed", project_root=project_root, config=config,
                          agent=agent, recipient=recipient, returncode=result.returncode,
                          stderr=result.stderr[:500])
        except Exception as exc:
            failed.append(recipient)
            audit_log("stop_notify_failed", project_root=project_root, config=config,
                      agent=agent, recipient=recipient, error=str(exc))
    trace_hook(hook="stop_notify", agent=agent, decision="notify",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               recipients=recipients, failed=failed)
    print("{}")
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # P4: advisory — fail-open
