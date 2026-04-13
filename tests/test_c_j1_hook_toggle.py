#!/usr/bin/env python3
"""Test C-J1: hook runtime toggle via flag files."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
CTL = ROOT / "scripts" / "orchestratorctl.py"
HOOK = ROOT / "hooks" / "dispatch_gate.py"

_CONFIG = {
    "project": "j1-test",
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
        "trackers": ".orchestrator/trackers.json",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
    },
    "agents": [{"name": "gate-ralph", "executor": True}],
    "gate": {},
    "routing": {},
    "fan_in": {},
    "wake": {},
    "session": {"session_prefix": "gate-"},
}


def setup(tmp: Path):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    (tmp / ".orchestrator" / "runtime_flags" / "hooks").mkdir(parents=True, exist_ok=True)
    for sub in ["inbox", "outbox"]:
        (tmp / "dispatch" / "gate-ralph" / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "dispatch" / "gate-ralph" / "ready").write_text("1", encoding="utf-8")


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


if __name__ == "__main__":
    passed = True

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        setup(tmp)

        # dispatch_gate should DENY (no inbox) when not disabled
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.py", "content": ""}})
        r = subprocess.run(
            [sys.executable, str(HOOK)],
            input=payload, capture_output=True, text=True,
            env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
            cwd=str(tmp),
        )
        passed &= check("dispatch_gate denies normally", r.returncode == 2,
                        f"exit={r.returncode}")

        # Disable dispatch_gate via flag file
        disable_flag = tmp / ".orchestrator" / "runtime_flags" / "hooks" / "dispatch_gate.disabled"
        disable_flag.write_text("disabled by test", encoding="utf-8")

        r2 = subprocess.run(
            [sys.executable, str(HOOK)],
            input=payload, capture_output=True, text=True,
            env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
            cwd=str(tmp),
        )
        passed &= check("dispatch_gate allows when disabled", r2.returncode == 0,
                        f"exit={r2.returncode}")

        # toggle-hook CLI: enable (remove flag)
        r3 = subprocess.run(
            [sys.executable, str(CTL), "toggle-hook", str(tmp),
             "--hook", "dispatch_gate", "--enable"],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("toggle-hook --enable exits 0", r3.returncode == 0,
                        f"exit={r3.returncode} stderr={r3.stderr[:200]}")
        passed &= check("flag file removed", not disable_flag.exists())

        # toggle-hook CLI: disable (create flag)
        r4 = subprocess.run(
            [sys.executable, str(CTL), "toggle-hook", str(tmp),
             "--hook", "dispatch_gate", "--disable"],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("toggle-hook --disable exits 0", r4.returncode == 0)
        passed &= check("flag file created", disable_flag.exists())

    sys.exit(0 if passed else 1)
