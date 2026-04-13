#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import subprocess
import time as _time

from lib.common import load_project_config, resolve_project_root, resolve_shared_roots, trace_hook

def main() -> int:
    if not os.environ.get('GATE_AGENT_NAME', '').strip():
        sys.exit(0)

    from lib.common import is_hook_disabled
    if is_hook_disabled("stop_notify"):
        sys.exit(0)

    _t0 = _time.monotonic()
    project_root = resolve_project_root()
    config = load_project_config(project_root)
    orch_root, _ = resolve_shared_roots(config)
    send_py = orch_root / "scripts" / "send.py"
    agent = os.environ.get("GATE_AGENT_NAME", "unknown").strip() or "unknown"
    recipients = list(config.get("routing", {}).get("on_stop", []))
    for recipient in recipients:
        try:
            subprocess.run(
                [sys.executable, str(send_py), "--project", str(project_root), recipient, f"{agent} stopped unexpectedly", "--type", "stop_event"],
                text=True,
                capture_output=True,
                timeout=5,
                env={**os.environ, "GATE_AGENT_NAME": agent},
            )
        except Exception:
            pass
    trace_hook(hook="stop_notify", agent=agent, decision="notify",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               recipients=recipients)
    print("{}")
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # P4: advisory — fail-open
