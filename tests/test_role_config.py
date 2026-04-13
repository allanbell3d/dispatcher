#!/usr/bin/env python3
"""Role/reviewer activation config tests."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from scripts.validate import validate_config


def _schema() -> dict:
    return json.loads((ROOT / "schemas" / "config_schema.json").read_text(encoding="utf-8"))


def _base_config() -> dict:
    return {
        "project": "role-config-test",
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
                "hybrid_a": ["gate-architect", "gate-codex-critic"],
            },
        },
    }


def test_validate_config_accepts_reviewers_block():
    config = _base_config()
    warnings: list[str] = []
    errors = validate_config(config, _schema(), [a["name"] for a in config["agents"]], warnings)
    assert errors == []


def test_validate_config_rejects_unknown_active_reviewer():
    config = _base_config()
    config["reviewers"]["active"] = ["gate-architect", "gate-missing"]
    warnings: list[str] = []
    errors = validate_config(config, _schema(), [a["name"] for a in config["agents"]], warnings)
    assert any("reviewers.active" in err and "gate-missing" in err for err in errors)


def test_validate_config_rejects_empty_active_reviewers():
    config = _base_config()
    config["reviewers"]["active"] = []
    warnings: list[str] = []
    errors = validate_config(config, _schema(), [a["name"] for a in config["agents"]], warnings)
    assert any("reviewers.active" in err for err in errors)


def test_validate_config_rejects_invalid_preset_member():
    config = _base_config()
    config["reviewers"]["presets"]["broken"] = ["gate-critic", "gate-ghost"]
    warnings: list[str] = []
    errors = validate_config(config, _schema(), [a["name"] for a in config["agents"]], warnings)
    assert any("reviewers.presets.broken" in err and "gate-ghost" in err for err in errors)
