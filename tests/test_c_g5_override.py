#!/usr/bin/env python3
"""Test C-G5: override command writes manual verdict."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
CTL = ROOT / "scripts" / "orchestratorctl.py"

_CONFIG = {
    "project": "g5-test",
    "shared_roots": {
        "orchestrator_primary": str(ROOT),
        "orchestrator_fallback": str(ROOT),
        "agents_primary": str(ROOT),
        "agents_fallback": str(ROOT),
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "current_task": ".orchestrator/current_task.json",
        "merged_verdicts": ".orchestrator/merged_verdicts",
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
        (tmp / ".orchestrator" / "merged_verdicts").mkdir(parents=True, exist_ok=True)

        r = subprocess.run(
            [sys.executable, str(CTL), "override", str(tmp), "--task", "T42", "--verdict", "approved"],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("override exits 0", r.returncode == 0,
                        f"exit={r.returncode} stderr={r.stderr[:200]}")

        verdict_file = tmp / ".orchestrator" / "merged_verdicts" / "T42.json"
        passed &= check("verdict file created", verdict_file.exists())

        if verdict_file.exists():
            data = json.loads(verdict_file.read_text(encoding="utf-8"))
            passed &= check("verdict is approved", data.get("verdict") == "approved")
            passed &= check("has override flag", data.get("override") is True)
            passed &= check("has by field", data.get("by") == "allan")
            passed &= check("has task_id", data.get("task_id") == "T42")
            passed &= check("has timestamp", "ts" in data)

        # Override with rejected
        r2 = subprocess.run(
            [sys.executable, str(CTL), "override", str(tmp), "--task", "T99", "--verdict", "rejected",
             "--reason", "code quality"],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("override rejected exits 0", r2.returncode == 0)
        vf2 = tmp / ".orchestrator" / "merged_verdicts" / "T99.json"
        if vf2.exists():
            data2 = json.loads(vf2.read_text(encoding="utf-8"))
            passed &= check("rejected verdict stored", data2.get("verdict") == "rejected")
            passed &= check("reason stored", data2.get("reason") == "code quality")

    sys.exit(0 if passed else 1)
