#!/usr/bin/env python3
"""Test B3: DELIVERED state in dispatch_gate.py — tracker-based detection."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
HOOK = ROOT / "hooks/dispatch_gate.py"

_CONFIG = {
    "project": "b3-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents"
    },
    "paths": {
        "state_root": ".orchestrator", "dispatch_root": "dispatch",
        "current_task": ".orchestrator/current_task.json",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts", "audit_log": ".orchestrator/audit.log",
        "trackers": ".orchestrator/trackers.json",
        "runtime_flags": ".orchestrator/runtime_flags", "logs": ".orchestrator/logs",
    },
    "agents": [{"name": "gate-ralph", "executor": True}],
    "gate": {"protected_branches": ["dev", "main"], "consensus_rule": "unanimous",
             "require_approvals_from": ["gate-architect"], "max_rework_rounds": 3},
    "routing": {"cc_all": [], "escalation_target": "allan"},
    "fan_in": {}, "wake": {}, "session": {"session_prefix": "gate-"},
}

_TRACKER_ENTRY = {
    "request_id": "T42", "msg_type": "review_request",
    "sender": "gate-ralph", "required": ["gate-architect"],
    "timeout_seconds": 300, "on_timeout": "escalate_allan",
    "original_body": "Review T42.", "created_at": 0.0,
    "received": {}, "escalated": False,
}

def setup(tmp: Path, *, has_tracker=False, has_verdict=False, has_inbox=False):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator/config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    (tmp / ".orchestrator/current_task.json").write_text(
        json.dumps({"id": "T42"}), encoding="utf-8"
    )
    if has_tracker:
        (tmp / ".orchestrator/trackers.json").write_text(
            json.dumps({"T42": _TRACKER_ENTRY}), encoding="utf-8"
        )
    if has_verdict:
        vdir = tmp / ".orchestrator/merged_verdicts"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "T42.json").write_text(
            json.dumps({"task_id": "T42", "verdict": "approved"}), encoding="utf-8"
        )
    dispatch = tmp / "dispatch/gate-ralph"
    for sub in ["inbox", "outbox"]:
        (dispatch / sub).mkdir(parents=True, exist_ok=True)
    (dispatch / "ready").touch()
    if has_inbox:
        (dispatch / "inbox/task_T42.md").write_text(
            "FROM: dispatcher\nTYPE: task\n---\nDo the thing", encoding="utf-8"
        )

def run(tmp: Path, tool_name: str, tool_input: dict = None):
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input or {}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True,
        env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
        cwd=str(tmp),
    )

def check(label, result, expect_exit):
    ok = result.returncode == expect_exit
    print(f"{'PASS' if ok else 'FAIL'}: {label} (exit={result.returncode}, want={expect_exit})")
    if not ok:
        print(f"  stdout: {result.stdout[:200]}")
        print(f"  stderr: {result.stderr[:200]}")
    return ok

if __name__ == "__main__":
    passed = True
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # tracker present + no verdict + Write -> DELIVERED deny (exit 2)
        setup(tmp, has_tracker=True)
        passed &= check("DELIVERED: Write denied", run(tmp, "Write"), 2)

        # tracker present + no verdict + git commit -> DELIVERED allow (exit 0)
        setup(tmp, has_tracker=True)
        passed &= check("DELIVERED: git commit allowed",
                        run(tmp, "Bash", {"command": "git commit -m 'fix: done'"}), 0)

        # tracker present + verdict exists -> falls to WAITING denied (inbox empty)
        setup(tmp, has_tracker=True, has_verdict=True)
        passed &= check("verdict present: WAITING deny", run(tmp, "Write"), 2)

        # no tracker + empty inbox -> WAITING denied
        setup(tmp)
        passed &= check("no tracker: WAITING deny", run(tmp, "Write"), 2)

        # no tracker + inbox has file -> WORKING allow
        setup(tmp, has_inbox=True)
        passed &= check("WORKING: Write allowed", run(tmp, "Write"), 0)

        # malformed stdin -> allow (exit 0) — hook should not crash
        setup(tmp, has_inbox=True)
        r = subprocess.run(
            [sys.executable, str(HOOK)],
            input="NOT VALID JSON",
            capture_output=True, text=True,
            env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
            cwd=str(tmp),
        )
        passed &= check("malformed stdin -> allow", r, 0)

    sys.exit(0 if passed else 1)
