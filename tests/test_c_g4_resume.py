#!/usr/bin/env python3
"""Test C-G4: resume command clears halt flags."""
import json, os, subprocess, sys, tempfile
from uuid import uuid4
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
REPO_ROOT = Path(__file__).resolve().parents[1]
CTL = REPO_ROOT / "scripts" / "orchestratorctl.py"
TMP_ROOT = Path(tempfile.gettempdir()) / "dispatcher-slice-tests"

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
        "current_task": ".orchestrator/tasks/current_task.json",
        "halts": ".orchestrator/halts",
        "audit_log": ".orchestrator/audit.log",
        "decision_trace": ".orchestrator/logs/decision_trace.log",
        "logs": ".orchestrator/logs",
    },
    "agents": [{"name": "gate-ralph", "executor": True}],
    "gate": {"require_approvals_from": ["gate-architect", "gate-critic"]},
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

    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = TMP_ROOT / f"resume-{uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=False)
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    halts_dir = tmp / ".orchestrator" / "halts"
    halts_dir.mkdir(parents=True, exist_ok=True)
    halt_file = halts_dir / "gate-ralph.flag"
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

    # Re-fan-out uses current_task.task_id, not the agent name
    (tmp / ".orchestrator" / "tasks").mkdir(parents=True, exist_ok=True)
    current_task = tmp / ".orchestrator" / "tasks" / "current_task.json"
    current_task.write_text(json.dumps({"task_id": "T99"}), encoding="utf-8")
    for reviewer in ["gate-architect", "gate-critic"]:
        (tmp / "dispatch" / reviewer / "inbox").mkdir(parents=True, exist_ok=True)
        for msg in (tmp / "dispatch" / reviewer / "inbox").glob("resume_*.md"):
            msg.unlink()

    r3 = subprocess.run(
        [sys.executable, str(CTL), "resume", str(tmp), "--agent", "gate-ralph", "--refan"],
        capture_output=True, text=True, cwd=str(tmp),
    )
    passed &= check("resume refan exits 0", r3.returncode == 0,
                    f"exit={r3.returncode} stderr={r3.stderr[:200]}")
    for reviewer in ["gate-architect", "gate-critic"]:
        msg = tmp / "dispatch" / reviewer / "inbox" / f"resume_T99_{reviewer}.md"
        passed &= check(f"refan wrote {reviewer} message", msg.exists(), str(msg))
        if msg.exists():
            body = msg.read_text(encoding="utf-8")
            passed &= check("refan uses task_id", "TASK_ID: T99" in body, body[:200])
            passed &= check("refan does not guess agent name", "gate-ralph" not in body.lower(), body[:200])

    current_task.write_text(json.dumps({}), encoding="utf-8")
    for reviewer in ["gate-architect", "gate-critic"]:
        for msg in (tmp / "dispatch" / reviewer / "inbox").glob("resume_*.md"):
            msg.unlink()

    r4 = subprocess.run(
        [sys.executable, str(CTL), "resume", str(tmp), "--agent", "gate-ralph", "--refan"],
        capture_output=True, text=True, cwd=str(tmp),
    )
    passed &= check("refan without task skips", r4.returncode == 0,
                    f"exit={r4.returncode} stdout={r4.stdout[:200]}")
    for reviewer in ["gate-architect", "gate-critic"]:
        passed &= check(f"no fallback resume file for {reviewer}",
                        not any((tmp / "dispatch" / reviewer / "inbox").glob("resume_*.md")),
                        str(list((tmp / "dispatch" / reviewer / "inbox").glob("resume_*.md"))))

    sys.exit(0 if passed else 1)
