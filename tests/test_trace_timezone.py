#!/usr/bin/env python3
"""Trace hook should honor configured timezone when config is available."""

import json
import os
import shutil
import uuid
from pathlib import Path

from lib.common import load_project_config, resolve_project_root, trace_hook


CONFIG = {
    "project": "trace-timezone-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents",
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
        "playwright_tests": "tests/e2e",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
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
    "agents": [{"name": "gate-ralph", "profile": "gate-ralph", "executor": True, "roles": ["coder"]}],
    "routing": {"cc_all": [], "review_requests_to": [], "escalation_target": "allan"},
    "gate": {"require_approvals_from": [], "consensus_rule": "unanimous", "max_rework_rounds": 3, "protected_branches": ["dev", "main"]},
    "fan_in": {"review": {"required": [], "timeout_seconds": 300, "on_timeout": "escalate_allan"}},
}


def test_trace_hook_uses_configured_timezone_when_config_is_loaded():
    base = Path(__file__).resolve().parents[1] / ".pytest_tmp_trace_tz"
    base.mkdir(parents=True, exist_ok=True)
    project = base / f"case_{uuid.uuid4().hex}"
    project.mkdir(parents=True, exist_ok=True)
    previous_cwd = Path.cwd()
    try:
        (project / ".orchestrator" / "logs").mkdir(parents=True, exist_ok=True)
        (project / ".orchestrator" / "config.json").write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")
        os.chdir(project)
        config = load_project_config(resolve_project_root(project))
        trace_hook(
            hook="timezone-test",
            agent="gate-ralph",
            decision="allow",
            elapsed_ms=1.0,
            project_root=project,
            config=config,
        )
        trace_path = project / ".orchestrator" / "logs" / "decision_trace.log"
        entry = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert entry["ts"].endswith("+04:00")
    finally:
        os.chdir(previous_cwd)
        shutil.rmtree(project, ignore_errors=True)
        if base.exists() and not any(base.iterdir()):
            base.rmdir()
