#!/usr/bin/env python3
"""Idle projects without task bootstrap should validate with warnings, not fail."""

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate.py"


CONFIG = {
    "project": "idle-project-test",
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
        "logs": ".orchestrator/logs",
        "audit_log": ".orchestrator/audit.log",
        "decision_trace": ".orchestrator/logs/decision_trace.log",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "runtime_flags": ".orchestrator/runtime_flags",
        "playwright_tests": "tests/e2e",
    },
    "wake": {
        "mechanism": "psmux",
        "first_attempt_seconds": 15,
        "retry_interval_seconds": 10,
        "max_retries": 30,
        "monitor_pulse_seconds": 30,
        "idle_threshold_seconds": 120,
        "liveness_check_interval_seconds": 30,
    },
    "session": {
        "require_ready_files": False,
        "halt_between_batches": True,
        "session_prefix": "gate-",
        "timezone": "Asia/Dubai",
    },
    "agents": [
        {"name": "gate-ralph", "profile": "gate-ralph", "executor": True, "roles": ["coder"]},
        {"name": "gate-architect", "profile": "gate-architect", "executor": False, "roles": ["reviewer"]},
        {"name": "gate-critic", "profile": "gate-critic", "executor": False, "roles": ["reviewer"]},
        {"name": "gate-monitor", "profile": "gate-monitor", "executor": False, "roles": ["monitor"]},
        {"name": "gate-playwright", "profile": "gate-playwright", "executor": False, "roles": ["playwright"]},
    ],
    "reviewers": {
        "available": ["gate-architect", "gate-critic"],
        "active": ["gate-architect", "gate-critic"],
        "presets": {"classic": ["gate-architect", "gate-critic"]},
    },
    "routing": {
        "cc_all": ["gate-monitor"],
        "review_requests_to": ["gate-architect", "gate-critic"],
        "escalation_target": "allan",
        "on_batch_complete": ["gate-playwright"],
        "on_test_failure": ["gate-ralph"],
        "on_test_passed": ["gate-ralph"],
        "on_stop": ["gate-monitor"],
    },
    "gate": {
        "require_approvals_from": ["gate-architect", "gate-critic"],
        "consensus_rule": "unanimous",
        "max_rework_rounds": 3,
        "protected_branches": ["dev", "main"],
    },
    "fan_in": {
        "review": {
            "required": ["gate-architect", "gate-critic"],
            "timeout_seconds": 300,
            "on_timeout": "escalate_allan",
        }
    },
}


def _make_project() -> Path:
    base = ROOT / ".pytest_tmp_validate_idle"
    project = base / f"idle_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    for relative in (
        ".orchestrator/plans",
        ".orchestrator/tasks",
        ".orchestrator/diffs",
        ".orchestrator/merged_verdicts",
        ".orchestrator/halts",
        ".orchestrator/runtime_flags",
        ".orchestrator/logs",
        "dispatch/gate-ralph/inbox",
        "dispatch/gate-ralph/outbox",
        "dispatch/gate-ralph/reports",
        "dispatch/gate-ralph/done",
        "dispatch/gate-ralph/archive",
        "dispatch/gate-architect/inbox",
        "dispatch/gate-architect/outbox",
        "dispatch/gate-architect/reports",
        "dispatch/gate-architect/done",
        "dispatch/gate-architect/archive",
        "dispatch/gate-critic/inbox",
        "dispatch/gate-critic/outbox",
        "dispatch/gate-critic/reports",
        "dispatch/gate-critic/done",
        "dispatch/gate-critic/archive",
        "dispatch/gate-monitor/inbox",
        "dispatch/gate-monitor/outbox",
        "dispatch/gate-monitor/reports",
        "dispatch/gate-monitor/done",
        "dispatch/gate-monitor/archive",
        "dispatch/gate-playwright/inbox",
        "dispatch/gate-playwright/outbox",
        "dispatch/gate-playwright/reports",
        "dispatch/gate-playwright/done",
        "dispatch/gate-playwright/archive",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)
    (project / ".orchestrator" / "config.json").write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")
    return project


def test_validate_accepts_idle_project_without_tasks_or_current_task():
    project = _make_project()
    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATE), str(project)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "RESULT: PASS" in output
        assert "no task" in output.lower()
    finally:
        shutil.rmtree(project, ignore_errors=True)
