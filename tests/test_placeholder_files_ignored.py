#!/usr/bin/env python3
"""Placeholder files like .gitkeep must not count as live dispatch artifacts."""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPATCH_GATE = ROOT / "hooks" / "dispatch_gate.py"
WATCHER = ROOT / "scripts" / "watcher.py"


CONFIG = {
    "project": "placeholder-ignore-test",
    "shared_roots": {
        "orchestrator_primary": str(ROOT),
        "orchestrator_fallback": str(ROOT),
        "agents_primary": str(ROOT),
        "agents_fallback": str(ROOT),
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "plans": ".orchestrator/plans",
        "tasks": ".orchestrator/tasks",
        "current_task": ".orchestrator/tasks/current_task.json",
        "trackers": ".orchestrator/trackers.json",
        "diffs": ".orchestrator/diffs",
        "audit_log": ".orchestrator/audit.log",
        "decision_trace": ".orchestrator/logs/decision_trace.log",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True, "roles": ["coder"]},
        {"name": "gate-architect", "executor": False, "roles": ["reviewer"]},
    ],
    "routing": {
        "cc_all": [],
        "review_requests_to": ["gate-architect"],
        "escalation_target": "allan",
    },
    "gate": {
        "require_approvals_from": ["gate-architect"],
        "consensus_rule": "unanimous",
        "max_rework_rounds": 3,
        "protected_branches": ["dev", "main"],
    },
    "fan_in": {
        "review": {
            "required": ["gate-architect"],
            "timeout_seconds": 300,
            "on_timeout": "escalate_allan",
        }
    },
    "wake": {
        "mechanism": "psmux",
        "first_attempt_seconds": 999,
        "retry_interval_seconds": 999,
        "max_retries": 0,
        "monitor_pulse_seconds": 999,
        "idle_threshold_seconds": 120,
        "liveness_check_interval_seconds": 999,
    },
    "session": {
        "require_ready_files": False,
        "session_prefix": "gate-",
        "timezone": "Asia/Dubai",
    },
}


def _make_project(name: str) -> Path:
    base = ROOT / ".pytest_tmp_placeholder_checks"
    project = base / f"{name}_{uuid.uuid4().hex}"
    for relative in (
        ".orchestrator/logs",
        ".orchestrator/runtime_flags",
        ".orchestrator/tasks",
        "dispatch/gate-ralph/inbox",
        "dispatch/gate-ralph/outbox",
        "dispatch/gate-ralph/reports",
        "dispatch/gate-ralph/archive",
        "dispatch/gate-ralph/done",
        "dispatch/gate-architect/inbox",
        "dispatch/gate-architect/outbox",
        "dispatch/gate-architect/reports",
        "dispatch/gate-architect/archive",
        "dispatch/gate-architect/done",
        "dispatch/allan/inbox",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)
    (project / ".orchestrator" / "config.json").write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")
    (project / ".orchestrator" / "tasks" / "current_task.json").write_text(json.dumps({}), encoding="utf-8")
    return project


def test_dispatch_gate_ignores_gitkeep_placeholder_in_inbox():
    project = _make_project("dispatch_gate")
    try:
        (project / "dispatch" / "gate-ralph" / "ready").write_text("1", encoding="utf-8")
        (project / "dispatch" / "gate-ralph" / "inbox" / ".gitkeep").write_text("\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(DISPATCH_GATE)],
            input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": "app.py", "content": "x"}}),
            capture_output=True,
            text=True,
            cwd=str(project),
            env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
        )
        assert result.returncode == 2
        assert "WAITING" in result.stderr
    finally:
        import shutil
        shutil.rmtree(project, ignore_errors=True)


def test_watcher_ignores_gitkeep_placeholder_in_reports():
    project = _make_project("watcher")
    process = subprocess.Popen(
        [sys.executable, str(WATCHER), str(project)],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        (project / "dispatch" / "gate-architect" / "reports" / ".gitkeep").write_text("\n", encoding="utf-8")
        time.sleep(2)
        (project / ".orchestrator" / "runtime_flags" / "STOP").write_text("stop", encoding="utf-8")
        stdout, stderr = process.communicate(timeout=10)
        log_path = project / ".orchestrator" / "logs" / "watcher.log"
        log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else stdout + "\n" + stderr
        assert "unmatched report left in place: .gitkeep" not in log_text
    finally:
        if process.poll() is None:
            (project / ".orchestrator" / "runtime_flags" / "STOP").write_text("stop", encoding="utf-8")
            process.wait(timeout=10)
        import shutil
        shutil.rmtree(project, ignore_errors=True)
