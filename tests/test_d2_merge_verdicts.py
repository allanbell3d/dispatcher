#!/usr/bin/env python3
"""Test D2: Watcher writes merged_verdicts/<task_id>.json on fan-in completion.
Covers: unanimous approve, unanimous reject, majority rule, any_pass rule.
Uses subprocess invocation — no package imports required.
"""
import json, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
WATCHER = ROOT / "scripts/watcher.py"

_CONFIG_BASE = {
    "project": "d2-test",
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
    "agents": [
        {"name": "gate-ralph", "executor": True},
        {"name": "gate-architect", "executor": False},
        {"name": "gate-monitor-1", "executor": False},
    ],
    "routing": {"cc_all": ["gate-monitor-1"], "escalation_target": "allan",
                "review_requests_to": ["gate-architect"]},
    "wake": {"mechanism": "tmux", "first_attempt_seconds": 999, "retry_interval_seconds": 999,
             "max_retries": 0, "monitor_pulse_seconds": 999},
    "session": {"require_ready_files": False, "session_prefix": "gate-", "timezone": "UTC"},
}

def make_report(reviewer: str, task_id: str, verdict: str) -> str:
    return (f"FROM: {reviewer}\nTO: ralph\nTYPE: review_response\n"
            f"TASK_ID: {task_id}\nVERDICT: {verdict}\n---\nFeedback body.")

def setup_dir(tmp: Path):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator/logs").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator/runtime_flags").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator/merged_verdicts").mkdir(parents=True, exist_ok=True)
    for agent in ["gate-ralph", "gate-architect", "gate-monitor-1", "allan"]:
        for sub in ["inbox", "outbox", "reports", "done", "archive"]:
            (tmp / "dispatch" / agent / sub).mkdir(parents=True, exist_ok=True)
        (tmp / "dispatch" / agent / "ready").touch()

def write_config(tmp: Path, consensus_rule: str, required: list):
    cfg = dict(_CONFIG_BASE)
    cfg["gate"] = {"protected_branches": ["dev", "main"], "consensus_rule": consensus_rule,
                   "require_approvals_from": required, "max_rework_rounds": 3}
    cfg["fan_in"] = {"review": {"required": required, "timeout_seconds": 300,
                                "on_timeout": "escalate_allan"}}
    (tmp / ".orchestrator/config.json").write_text(json.dumps(cfg), encoding="utf-8")

def add_tracker(tmp: Path, task_id: str, required: list):
    import time as _t
    trackers = {}
    try:
        trackers = json.loads((tmp / ".orchestrator/trackers.json").read_text())
    except Exception:
        pass
    trackers[task_id] = {
        "request_id": task_id, "msg_type": "review_request",
        "sender": "gate-ralph", "required": required,
        "timeout_seconds": 300, "on_timeout": "escalate_allan",
        "original_body": f"Review {task_id}.",
        "created_at": _t.time(), "received": {}, "escalated": False,
    }
    (tmp / ".orchestrator/trackers.json").write_text(json.dumps(trackers), encoding="utf-8")

def run_watcher(tmp: Path, seconds: float = 10.0):
    stop_file = tmp / ".orchestrator/runtime_flags/STOP"
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    verdict_dir = tmp / ".orchestrator/merged_verdicts"
    # Count existing verdicts before starting
    existing = len(list(verdict_dir.glob("*.json"))) if verdict_dir.exists() else 0
    proc = subprocess.Popen(
        [sys.executable, str(WATCHER)],
        cwd=str(tmp), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Poll for new verdict file instead of sleeping a fixed duration
    deadline = time.time() + seconds
    while time.time() < deadline:
        current = len(list(verdict_dir.glob("*.json"))) if verdict_dir.exists() else 0
        if current > existing:
            break
        time.sleep(0.3)
    stop_file.touch()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    if stop_file.exists():
        stop_file.unlink()

def check(label, condition, detail=""):
    ok = bool(condition)
    print(f"{'PASS' if ok else 'FAIL'}: {label}" + (f" ({detail})" if detail else ""))
    return ok

def write_report(tmp: Path, reviewer: str, task_id: str, verdict: str):
    path = tmp / "dispatch" / reviewer / "reports" / f"{task_id}_review.md"
    path.write_text(make_report(reviewer, task_id, verdict), encoding="utf-8")

if __name__ == "__main__":
    passed = True
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        setup_dir(tmp)

        # --- Test 1: unanimous — single reviewer approves ---
        write_config(tmp, "unanimous", ["gate-architect"])
        add_tracker(tmp, "T42", ["gate-architect"])
        write_report(tmp, "gate-architect", "T42", "approved")
        run_watcher(tmp)

        vf = tmp / ".orchestrator/merged_verdicts/T42.json"
        passed &= check("T42 verdict file created", vf.exists())
        if vf.exists():
            v = json.loads(vf.read_text())
            passed &= check("unanimous approve -> approved", v.get("verdict") == "approved",
                            v.get("verdict"))
            passed &= check("consensus_rule in verdict", "consensus_rule" in v)
            passed &= check("verdicts map in verdict", "verdicts" in v)
            passed &= check("dissent empty", v.get("dissent") == [], str(v.get("dissent")))

        # --- Test 2: unanimous — single reviewer rejects ---
        write_config(tmp, "unanimous", ["gate-architect"])
        add_tracker(tmp, "T43", ["gate-architect"])
        write_report(tmp, "gate-architect", "T43", "rejected")
        run_watcher(tmp)

        vf2 = tmp / ".orchestrator/merged_verdicts/T43.json"
        passed &= check("T43 verdict file created", vf2.exists())
        if vf2.exists():
            v2 = json.loads(vf2.read_text())
            passed &= check("unanimous reject -> rejected", v2.get("verdict") == "rejected",
                            v2.get("verdict"))
            passed &= check("dissent contains gate-architect",
                            "gate-architect" in v2.get("dissent", []))

        # --- Test 3: majority — 1/2 approves -> rejected (strict majority needs >50%) ---
        write_config(tmp, "majority", ["gate-architect", "gate-monitor-1"])
        add_tracker(tmp, "T44", ["gate-architect", "gate-monitor-1"])
        write_report(tmp, "gate-architect", "T44", "approved")
        write_report(tmp, "gate-monitor-1", "T44", "rejected")
        run_watcher(tmp)

        vf3 = tmp / ".orchestrator/merged_verdicts/T44.json"
        passed &= check("T44 verdict file created", vf3.exists())
        if vf3.exists():
            v3 = json.loads(vf3.read_text())
            # 1 > 2/2 is False -> rejected (strict majority, tie goes to rejected)
            passed &= check("majority 1/2 -> rejected", v3.get("verdict") == "rejected",
                            v3.get("verdict"))

        # --- Test 4: any_pass — 1/2 approves -> approved ---
        write_config(tmp, "any_pass", ["gate-architect", "gate-monitor-1"])
        add_tracker(tmp, "T45", ["gate-architect", "gate-monitor-1"])
        write_report(tmp, "gate-architect", "T45", "approved")
        write_report(tmp, "gate-monitor-1", "T45", "rejected")
        run_watcher(tmp)

        vf4 = tmp / ".orchestrator/merged_verdicts/T45.json"
        passed &= check("T45 verdict file created", vf4.exists())
        if vf4.exists():
            v4 = json.loads(vf4.read_text())
            passed &= check("any_pass 1/2 approve -> approved", v4.get("verdict") == "approved",
                            v4.get("verdict"))

    sys.exit(0 if passed else 1)
