#!/usr/bin/env python3
"""Primary and fallback monitor stream checks."""

import copy
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MONITOR_INGEST = ROOT / "hooks" / "monitor_ingest.py"
ACTIVITY_LOGGER = ROOT / "hooks" / "activity_logger.py"
WATCHER = ROOT / "scripts" / "watcher.py"


def _config(*, fallback_stream: bool) -> dict:
    return {
        "project": "monitor-stream-test",
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
            "monitor_activity_to_dispatch": fallback_stream,
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


def _make_project(name: str, *, fallback_stream: bool) -> Path:
    base = ROOT / ".pytest_tmp_monitor_stream"
    project = base / f"{name}_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    for relative in (
        ".orchestrator/logs",
        ".orchestrator/runtime_flags",
        ".orchestrator/tasks",
        "lib",
        "scripts",
        "dispatch/gate-ralph/inbox",
        "dispatch/gate-ralph/outbox",
        "dispatch/gate-ralph/archive",
        "dispatch/gate-monitor/inbox",
        "dispatch/gate-monitor/outbox",
        "dispatch/allan/inbox",
        "dispatch/allan/outbox",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)
    config = copy.deepcopy(_config(fallback_stream=fallback_stream))
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
    shutil.copy2(ROOT / "lib" / "common.py", project / "lib" / "common.py")
    shutil.copy2(ROOT / "scripts" / "send.py", project / "scripts" / "send.py")
    (project / ".orchestrator" / "tasks" / "current_task.json").write_text(
        json.dumps({"task_id": "MON-1"}),
        encoding="utf-8",
    )
    return project


def _run_hook(script: Path, project: Path, payload: dict, *, agent: str = "gate-ralph") -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["GATE_AGENT_NAME"] = agent
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(project),
        env=env,
        timeout=15,
    )


def _wait_for(predicate, *, timeout: float = 10.0, interval: float = 0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return None


def test_monitor_ingest_primary_stream_writes_json_to_monitor_inbox():
    project = _make_project("primary", fallback_stream=False)
    try:
        result = _run_hook(
            MONITOR_INGEST,
            project,
            {
                "tool_name": "Bash",
                "tool_input": {"command": "echo hi"},
                "tool_response": {"output": "hi"},
                "exit_code": 0,
            },
        )
        assert result.returncode == 0, result.stderr
        inbox_files = sorted((project / "dispatch" / "gate-monitor" / "inbox").glob("*.json"))
        assert len(inbox_files) == 1
        payload = json.loads(inbox_files[0].read_text(encoding="utf-8"))
        assert payload["from"] == "gate-ralph"
        assert payload["tool"] == "Bash"
        assert payload["exit_code"] == 0
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_activity_logger_fallback_disabled_does_not_queue_dispatch_message():
    project = _make_project("fallback_off", fallback_stream=False)
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
        outbox_files = list((project / "dispatch" / "gate-ralph" / "outbox").glob("*.md"))
        assert outbox_files == []
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_activity_logger_fallback_stream_delivers_activity_message_via_watcher():
    project = _make_project("fallback_on", fallback_stream=True)
    process = None
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
        outbox_files = list((project / "dispatch" / "gate-ralph" / "outbox").glob("*.md"))
        assert len(outbox_files) == 1

        process = subprocess.Popen(
            [sys.executable, str(WATCHER), str(project)],
            cwd=str(project),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        delivered = _wait_for(
            lambda: sorted((project / "dispatch" / "gate-monitor" / "inbox").glob("*.md")),
            timeout=10,
        )
        assert delivered, "watcher did not deliver fallback activity message to monitor inbox"
        text = delivered[0].read_text(encoding="utf-8")
        assert "TYPE: activity" in text
        assert "FROM: gate-ralph" in text

        (project / ".orchestrator" / "runtime_flags" / "STOP").write_text("stop", encoding="utf-8")
        process.wait(timeout=10)
    finally:
        if process and process.poll() is None:
            (project / ".orchestrator" / "runtime_flags" / "STOP").write_text("stop", encoding="utf-8")
            process.wait(timeout=10)
        shutil.rmtree(project, ignore_errors=True)
