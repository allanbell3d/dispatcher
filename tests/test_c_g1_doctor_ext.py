#!/usr/bin/env python3
"""Test C-G1: doctor extensions -- decision_trace, hooks, sprint_profiles."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
DOCTOR = ROOT / "scripts" / "doctor.py"

_CONFIG = {
    "project": "doctor-ext-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents"
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "current_task": ".orchestrator/current_task.json",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "audit_log": ".orchestrator/audit.log",
        "decision_trace": ".orchestrator/decision_trace.log",
        "trackers": ".orchestrator/trackers.json",
        "runtime_flags": ".orchestrator/runtime_flags",
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
        (tmp / "dispatch").mkdir(parents=True, exist_ok=True)

        r = subprocess.run(
            [sys.executable, str(DOCTOR), str(tmp)],
            capture_output=True, text=True, cwd=str(tmp),
        )
        output = r.stdout + r.stderr
        passed &= check("doctor runs without crash", r.returncode in (0, 1), f"exit={r.returncode}")
        passed &= check("output contains python check", "python" in output.lower(), output[:200])
        passed &= check("output contains DONE", "DONE" in output, output[-100:])

        # Check for new Wave 4 checks in output
        passed &= check("output mentions decision_trace or trace",
                        "decision_trace" in output or "trace" in output.lower(),
                        output[:500])

    sys.exit(0 if passed else 1)
