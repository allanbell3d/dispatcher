#!/usr/bin/env python3
"""Observability checks for hook-generated logs."""

import copy
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPATCH_GATE = ROOT / "hooks" / "dispatch_gate.py"
ACTIVITY_LOGGER = ROOT / "hooks" / "activity_logger.py"
WATCHER = ROOT / "scripts" / "watcher.py"


BASE_CONFIG = {
    "project": "hook-observability-test",
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
    "wake": {
        "mechanism": "psmux",
        "first_attempt_seconds": 60,
        "retry_interval_seconds": 60,
        "max_retries": 1,
        "monitor_pulse_seconds": 60,
        "idle_threshold_seconds": 120,
        "liveness_check_interval_seconds": 60,
    },
    "session": {
        "require_ready_files": False,
        "halt_between_batches": True,
        "session_prefix": "gate-",
        "timezone": "Asia/Dubai",
    },
    "agents": [
        {"name": "gate-ralph", "profile": "gate-ralph", "executor": True, "roles": ["coder"]},
        {"name": "gate-monitor", "profile": "gate-monitor", "executor": False, "roles": ["monitor"]},
    ],
    "routing": {
        "cc_all": ["gate-monitor"],
        "review_requests_to": [],
        "escalation_target": "allan",
        "on_stop": ["gate-monitor"],
    },
    "gate": {
        "require_approvals_from": [],
        "consensus_rule": "unanimous",
        "max_rework_rounds": 3,
        "protected_branches": ["dev", "main"],
    },
    "fan_in": {"review": {"required": [], "timeout_seconds": 300, "on_timeout": "escalate_allan"}},
}


def _make_project(name: str) -> Path:
    base = ROOT / ".pytest_tmp_hook_observability"
    project = base / f"{name}_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    for relative in (
        ".orchestrator/logs",
        ".orchestrator/runtime_flags",
        ".orchestrator/tasks",
        "dispatch/gate-ralph/inbox",
        "dispatch/gate-ralph/outbox",
        "dispatch/gate-ralph/archive",
        "dispatch/gate-monitor/inbox",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)
    config = copy.deepcopy(BASE_CONFIG)
    config["shared_roots"] = {
        "orchestrator_primary": str(project),
        "orchestrator_fallback": str(project),
        "agents_primary": str(project),
        "agents_fallback": str(project),
    }
    (project / ".orchestrator" / "config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )
    (project / ".orchestrator" / "tasks" / "current_task.json").write_text(
        json.dumps({"task_id": "OBS-1"}),
        encoding="utf-8",
    )
    return project


def _run_hook(script: Path, project: Path, payload: dict, *, agent: str = "gate-ralph") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(project),
        env={"GATE_AGENT_NAME": agent},
        timeout=15,
    )


def _read_json_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(json.loads(line))
    return items


def test_dispatch_gate_writes_audit_and_trace_logs_for_working_agent():
    project = _make_project("dispatch_gate")
    try:
        (project / "dispatch" / "gate-ralph" / "ready").write_text("1", encoding="utf-8")
        (project / "dispatch" / "gate-ralph" / "inbox" / "task.md").write_text(
            "FROM: watcher\nTYPE: dispatch\nTASK_ID: OBS-1\n---\nwork\n",
            encoding="utf-8",
        )
        result = _run_hook(
            DISPATCH_GATE,
            project,
            {"tool_name": "Write", "tool_input": {"file_path": "app.py", "content": "print('ok')"}},
        )
        assert result.returncode == 0, result.stderr

        audit_entries = _read_json_lines(project / ".orchestrator" / "audit.log")
        assert any(
            entry.get("event") == "dispatch_gate"
            and entry.get("state") == "WORKING"
            and entry.get("action") == "allow"
            for entry in audit_entries
        )

        trace_entries = _read_json_lines(project / ".orchestrator" / "logs" / "decision_trace.log")
        assert any(
            entry.get("hook") == "dispatch_gate"
            and entry.get("state") == "WORKING"
            and entry.get("decision") == "allow"
            for entry in trace_entries
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_activity_logger_writes_activity_log_and_trace_without_happy_path_audit_log():
    project = _make_project("activity_logger")
    try:
        result = _run_hook(
            ACTIVITY_LOGGER,
            project,
            {
                "tool_name": "Bash",
                "tool_input": {"command": "echo hi"},
                "tool_response": {"output": "hi"},
                "exit_code": 0,
            },
        )
        assert result.returncode == 0, result.stderr

        activity_log = project / ".orchestrator" / "logs" / "activity_gate-ralph.log"
        assert activity_log.exists()
        activity_text = activity_log.read_text(encoding="utf-8")
        assert "tool_name" in activity_text
        assert "Bash" in activity_text

        trace_entries = _read_json_lines(project / ".orchestrator" / "logs" / "decision_trace.log")
        assert any(
            entry.get("hook") == "activity_logger" and entry.get("decision") == "allow"
            for entry in trace_entries
        )

        assert not (project / ".orchestrator" / "audit.log").exists()
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_watcher_creates_startup_log_on_boot():
    project = _make_project("watcher_boot")
    process = subprocess.Popen(
        [sys.executable, str(WATCHER), str(project)],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 10
        log_path = project / ".orchestrator" / "logs" / "watcher.log"
        while time.time() < deadline:
            if log_path.exists() and "Watcher started" in log_path.read_text(encoding="utf-8"):
                break
            time.sleep(0.25)
        else:
            raise AssertionError("watcher.log did not receive startup lines")

        (project / ".orchestrator" / "runtime_flags" / "STOP").write_text("stop", encoding="utf-8")
        process.wait(timeout=10)
        log_text = log_path.read_text(encoding="utf-8")
        assert "Watcher started" in log_text
        assert "Liveness ticker started" in log_text
    finally:
        if process.poll() is None:
            (project / ".orchestrator" / "runtime_flags" / "STOP").write_text("stop", encoding="utf-8")
            process.wait(timeout=10)
        shutil.rmtree(project, ignore_errors=True)
