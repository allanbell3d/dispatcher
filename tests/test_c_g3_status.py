#!/usr/bin/env python3
"""Test C-G3: status command in orchestratorctl."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
CTL = ROOT / "scripts" / "orchestratorctl.py"

_CONFIG = {
    "project": "g3-test",
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
        "trackers": ".orchestrator/trackers.json",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True},
        {"name": "gate-architect", "executor": False},
    ],
    "gate": {},
    "routing": {"cc_all": [], "escalation_target": "allan"},
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
        (tmp / ".orchestrator" / "halts").mkdir(parents=True, exist_ok=True)
        (tmp / ".orchestrator" / "current_task.json").write_text(
            json.dumps({"id": "T42", "title": "test task"}), encoding="utf-8"
        )
        for agent in ["gate-ralph", "gate-architect"]:
            for sub in ["inbox", "outbox"]:
                (tmp / "dispatch" / agent / sub).mkdir(parents=True, exist_ok=True)
        # Add a message to ralph's inbox
        (tmp / "dispatch" / "gate-ralph" / "inbox" / "test.md").write_text("msg", encoding="utf-8")
        # Halt gate-architect
        (tmp / ".orchestrator" / "halts" / "gate-architect.flag").write_text("test halt", encoding="utf-8")

        r = subprocess.run(
            [sys.executable, str(CTL), "status", str(tmp)],
            capture_output=True, text=True, cwd=str(tmp),
        )
        output = r.stdout
        passed &= check("status runs", r.returncode == 0,
                        f"exit={r.returncode} stderr={r.stderr[:200]}")
        passed &= check("shows ralph", "gate-ralph" in output, output[:500])
        passed &= check("shows gate-architect", "gate-architect" in output, output[:500])
        passed &= check("shows current task T42", "T42" in output, output[:500])
        passed &= check("shows halted state", "halt" in output.lower() or "HALTED" in output,
                        output[:500])
        passed &= check("shows inbox depth", "1" in output or "inbox" in output.lower(),
                        output[:500])

    sys.exit(0 if passed else 1)
