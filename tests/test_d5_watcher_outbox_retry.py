#!/usr/bin/env python3
"""Test D5: watcher preserves deferred review_request work in outbox."""
import json
import os
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHER = REPO_ROOT / "scripts" / "watcher.py"
TMP_ROOT = Path(tempfile.gettempdir()) / "dispatcher-slice-tests"

_CONFIG = {
    "project": "d5-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents",
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
    "routing": {
        "cc_all": [],
        "escalation_target": "allan",
        "review_requests_to": ["gate-architect"],
    },
    "fan_in": {
        "review": {
            "required": ["gate-architect"],
            "timeout_seconds": 300,
            "on_timeout": "escalate_allan",
        }
    },
    "wake": {
        "mechanism": "tmux",
        "first_attempt_seconds": 999,
        "retry_interval_seconds": 999,
        "max_retries": 0,
        "monitor_pulse_seconds": 999,
    },
    "session": {"require_ready_files": True, "session_prefix": "gate-", "timezone": "UTC"},
}


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


def setup(tmp: Path):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    for sub in ["logs", "runtime_flags", "merged_verdicts"]:
        (tmp / ".orchestrator" / sub).mkdir(parents=True, exist_ok=True)
    for agent in ["gate-ralph", "gate-architect", "allan"]:
        for sub in ["inbox", "outbox", "reports", "done", "archive"]:
            (tmp / "dispatch" / agent / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "dispatch" / "gate-ralph" / "outbox" / "T42_review.md").write_text(
        "FROM: gate-ralph\nTO: gate-architect\nTYPE: review_request\nTASK_ID: T42\n---\nPlease review.",
        encoding="utf-8",
    )


def run_watcher(tmp: Path, wait_seconds: float = 2.0):
    stop_file = tmp / ".orchestrator" / "runtime_flags" / "STOP"
    proc = subprocess.Popen(
        [sys.executable, str(WATCHER)],
        cwd=str(tmp),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ},
    )
    time.sleep(wait_seconds)
    stop_file.touch()
    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate(timeout=10)
    if stop_file.exists():
        stop_file.unlink()
    return proc.returncode, stdout, stderr


if __name__ == "__main__":
    passed = True
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = TMP_ROOT / f"watcher-{uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=False)
    setup(tmp)

    code, stdout, stderr = run_watcher(tmp)
    passed &= check("watcher exits 0", code == 0, f"exit={code} stderr={stderr[:200]}")

    log_file = tmp / ".orchestrator" / "logs" / "watcher.log"
    outbox_file = tmp / "dispatch" / "gate-ralph" / "outbox" / "T42_review.md"
    archive_dir = tmp / "dispatch" / "gate-ralph" / "archive"
    reviewer_inbox = tmp / "dispatch" / "gate-architect" / "inbox"

    log_text = log_file.read_text(encoding="utf-8") if log_file.exists() else "missing"
    passed &= check("watcher logged defer", log_file.exists() and "DEFER review_request" in log_text, log_text[:300])
    passed &= check("deferred review_request stays in outbox", outbox_file.exists(), str(outbox_file))
    passed &= check("no archive created for deferred review_request",
                    not any(archive_dir.glob("*")), str(list(archive_dir.glob("*"))))
    passed &= check("no reviewer inbox delivery when not ready",
                    not any(reviewer_inbox.glob("*")), str(list(reviewer_inbox.glob("*"))))

    sys.exit(0 if passed else 1)
