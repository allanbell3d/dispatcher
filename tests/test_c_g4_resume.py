#!/usr/bin/env python3
"""Test C-G4: resume command clears halt flags."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
CTL = ROOT / "scripts" / "orchestratorctl.py"

_CONFIG = {
    "project": "g4-test",
    "shared_roots": {
        "orchestrator_primary": str(ROOT),
        "orchestrator_fallback": str(ROOT),
        "agents_primary": str(ROOT),
        "agents_fallback": str(ROOT),
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "halts": ".orchestrator/halts",
        "audit_log": ".orchestrator/audit.log",
        "decision_trace": ".orchestrator/decision_trace.log",
        "logs": ".orchestrator/logs",
    },
    "agents": [{"name": "gate-ralph", "executor": True}],
    "gate": {},
    "routing": {},
    "fan_in": {},
    "wake": {},
    "session": {},
}


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


if __name__ == "__main__":
    passed = True

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
        (tmp / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
        halts_dir = tmp / ".orchestrator" / "halts"
        halts_dir.mkdir(parents=True, exist_ok=True)
        halt_file = halts_dir / "ralph.flag"
        halt_file.write_text("test halt reason", encoding="utf-8")

        passed &= check("halt file exists before resume", halt_file.exists())

        r = subprocess.run(
            [sys.executable, str(CTL), "resume", str(tmp), "--agent", "gate-ralph"],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("resume exits 0", r.returncode == 0,
                        f"exit={r.returncode} stderr={r.stderr[:200]}")
        passed &= check("halt file removed", not halt_file.exists())
        passed &= check("output confirms resume", "gate-ralph" in r.stdout.lower() or "resumed" in r.stdout.lower(),
                        r.stdout[:200])

        # Resume non-halted agent is a no-op (exit 0)
        r2 = subprocess.run(
            [sys.executable, str(CTL), "resume", str(tmp), "--agent", "gate-ralph"],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("resume non-halted is no-op", r2.returncode == 0)

    sys.exit(0 if passed else 1)
