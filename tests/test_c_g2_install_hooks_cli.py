#!/usr/bin/env python3
"""Test C-G2: install-hooks --all via orchestratorctl."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
CTL = ROOT / "scripts" / "orchestratorctl.py"

_CONFIG = {
    "project": "g2-test",
    "shared_roots": {
        "orchestrator_primary": str(ROOT),
        "orchestrator_fallback": str(ROOT),
        "agents_primary": str(ROOT),
        "agents_fallback": str(ROOT),
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True},
        {"name": "gate-architect", "executor": False},
    ],
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

        # install-hooks subcommand should exist and run
        r = subprocess.run(
            [sys.executable, str(CTL), "install-hooks", str(tmp)],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("install-hooks runs", r.returncode == 0,
                        f"exit={r.returncode} stderr={r.stderr[:200]}")
        # Output should mention agent names
        output = r.stdout
        passed &= check("output mentions ralph", "gate-ralph" in output, output[:300])
        passed &= check("gate-architect in --all output", "--- gate-architect ---" in output, output[:300])

        # install-hooks with --agent flag
        r2 = subprocess.run(
            [sys.executable, str(CTL), "install-hooks", str(tmp), "--agent", "gate-ralph"],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("install-hooks --agent runs", r2.returncode == 0,
                        f"exit={r2.returncode} stderr={r2.stderr[:200]}")
        # Output should be valid JSON for a single agent
        try:
            data = json.loads(r2.stdout)
            passed &= check("single agent output is JSON", True)
            passed &= check("has hooks key", "hooks" in data)
        except Exception as e:
            passed &= check("single agent output is JSON", False, str(e))

    sys.exit(0 if passed else 1)
