#!/usr/bin/env python3
"""Role activation CLI tests for scripts/orchestratorctl.py."""

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTL = ROOT / "scripts" / "orchestratorctl.py"


def _config() -> dict:
    return {
        "project": "roles-cli-test",
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
        "agents": [
            {"name": "gate-ralph", "profile": "gate-ralph", "executor": True, "roles": ["coder"]},
            {"name": "gate-architect", "profile": "gate-architect", "executor": False, "roles": ["reviewer"]},
            {"name": "gate-critic", "profile": "gate-critic", "executor": False, "roles": ["reviewer"]},
            {"name": "gate-codex-architect", "profile": "gate-codex-architect", "executor": False, "roles": ["reviewer"]},
            {"name": "gate-codex-critic", "profile": "gate-codex-critic", "executor": False, "roles": ["reviewer"]},
            {"name": "gate-monitor", "profile": "gate-monitor", "executor": False, "roles": ["monitor"]},
        ],
        "routing": {
            "cc_all": ["gate-monitor"],
            "review_requests_to": ["gate-architect", "gate-critic"],
            "escalation_target": "allan",
            "on_batch_complete": [],
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
        "reviewers": {
            "available": [
                "gate-architect",
                "gate-critic",
                "gate-codex-architect",
                "gate-codex-critic",
            ],
            "active": ["gate-architect", "gate-critic"],
            "presets": {
                "classic": ["gate-architect", "gate-critic"],
                "codex": ["gate-codex-architect", "gate-codex-critic"],
            },
        },
    }


def _project_dir() -> Path:
    base = ROOT / ".tmp_roles_cli"
    project = base / f"roles_{uuid.uuid4().hex}"
    project.mkdir(parents=True, exist_ok=True)
    (project / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (project / ".orchestrator" / "config.json").write_text(json.dumps(_config(), indent=2), encoding="utf-8")
    return project


def _run(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CTL), *args, str(project)],
        capture_output=True,
        text=True,
        cwd=str(project),
    )


def test_reviewers_show_outputs_active_and_presets():
    project = _project_dir()
    try:
        result = subprocess.run(
            [sys.executable, str(CTL), "reviewers", "show", str(project)],
            capture_output=True,
            text=True,
            cwd=str(project),
        )
        assert result.returncode == 0, result.stderr
        assert "active" in result.stdout.lower()
        assert "gate-architect" in result.stdout
        assert "codex" in result.stdout.lower()
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_reviewers_preset_updates_active_reviewers_and_derived_fields():
    project = _project_dir()
    try:
        result = subprocess.run(
            [sys.executable, str(CTL), "reviewers", "preset", "codex", str(project)],
            capture_output=True,
            text=True,
            cwd=str(project),
        )
        assert result.returncode == 0, result.stderr
        updated = json.loads((project / ".orchestrator" / "config.json").read_text(encoding="utf-8"))
        assert updated["reviewers"]["active"] == ["gate-codex-architect", "gate-codex-critic"]
        assert updated["routing"]["review_requests_to"] == ["gate-codex-architect", "gate-codex-critic"]
        assert updated["gate"]["require_approvals_from"] == ["gate-codex-architect", "gate-codex-critic"]
        assert updated["fan_in"]["review"]["required"] == ["gate-codex-architect", "gate-codex-critic"]
    finally:
        shutil.rmtree(project, ignore_errors=True)
