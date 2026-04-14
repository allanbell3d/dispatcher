#!/usr/bin/env python3
"""Integration checks for the consolidated monitor pipeline."""

import copy
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from scripts.install_hooks import build_hook_inventory


ROOT = Path(__file__).resolve().parents[1]
MONITOR_INGEST = ROOT / "hooks" / "monitor_ingest.py"


def _config(*, idle_seconds: int = 60) -> dict:
    return {
        "project": "monitor-integration-test",
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
            "idle_threshold_seconds": idle_seconds,
            "liveness_check_interval_seconds": 60,
        },
        "session": {
            "require_ready_files": False,
            "halt_between_batches": True,
            "session_prefix": "gate-",
            "timezone": "Asia/Dubai",
            "monitor_activity_to_dispatch": False,
        },
        "agents": [
            {"name": "gate-ralph", "profile": "gate-ralph", "executor": True, "roles": ["coder"]},
            {"name": "gate-architect", "profile": "gate-architect", "executor": False, "roles": ["reviewer"]},
            {"name": "gate-monitor", "profile": "gate-monitor", "executor": False, "roles": ["monitor"]},
        ],
        "routing": {
            "cc_all": ["gate-monitor"],
            "review_requests_to": ["gate-architect"],
            "escalation_target": "allan",
            "on_stop": ["gate-monitor"],
        },
        "gate": {
            "require_approvals_from": ["gate-architect"],
            "consensus_rule": "unanimous",
            "max_rework_rounds": 3,
            "protected_branches": ["dev", "main"],
        },
        "fan_in": {"review": {"required": ["gate-architect"], "timeout_seconds": 300, "on_timeout": "escalate_allan"}},
    }


def _make_project(name: str, *, idle_seconds: int = 60) -> Path:
    base = ROOT / ".pytest_tmp_monitor_integration"
    project = base / f"{name}_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    for relative in (
        ".orchestrator/logs",
        ".orchestrator/runtime_flags",
        ".orchestrator/tasks",
        "dispatch/gate-ralph/inbox",
        "dispatch/gate-ralph/outbox",
        "dispatch/gate-architect/inbox",
        "dispatch/gate-architect/outbox",
        "dispatch/gate-monitor/inbox",
        "dispatch/gate-monitor/outbox",
        "dispatch/allan/inbox",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)
    config = copy.deepcopy(_config(idle_seconds=idle_seconds))
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
    return project


def _write_transcript(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def _append_transcript(path: Path, records: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _run_hook(script: Path, project: Path, payload: dict, *, agent: str) -> subprocess.CompletedProcess[str]:
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


def _monitor_payloads(project: Path) -> list[dict]:
    payloads = []
    for path in sorted((project / "dispatch" / "gate-monitor" / "inbox").glob("*.json")):
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def _trace_rows(project: Path) -> list[dict]:
    path = project / ".orchestrator" / "logs" / "monitor_trace.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _session_payload(*, session_id: str, transcript_path: Path, tool_name: str = "Read") -> dict:
    return {
        "session_id": session_id,
        "transcript_path": str(transcript_path),
        "tool_name": tool_name,
        "tool_input": {"file_path": "docs/LOGGING_MONITOR_CONTRACT.md"},
        "tool_response": {"content": "ok"},
        "exit_code": 0,
    }


def test_monitor_ingest_writes_rendered_monitor_output_and_trace_log():
    project = _make_project("render_trace")
    transcript = project / "transcripts" / "ralph.jsonl"
    _write_transcript(
        transcript,
        [
            {
                "type": "user",
                "sessionId": "sess-ralph",
                "timestamp": "2026-04-14T10:00:00Z",
                "uuid": "u-1",
                "message": {"role": "user", "content": "Please investigate the monitor stream."},
            },
            {
                "type": "assistant",
                "sessionId": "sess-ralph",
                "timestamp": "2026-04-14T10:00:02Z",
                "uuid": "a-1",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "I am checking the latest pipeline.\n```python\nprint('trace')\n```"},
                        {"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {"file_path": "scripts/monitor_tail.py"}},
                    ],
                },
            },
        ],
    )

    result = _run_hook(
        MONITOR_INGEST,
        project,
        _session_payload(session_id="sess-ralph", transcript_path=transcript),
        agent="gate-ralph",
    )

    assert result.returncode == 0, result.stderr
    payloads = _monitor_payloads(project)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["from"] == "gate-ralph"
    assert payload["tool"] == "Read"
    assert payload["exit_code"] == 0
    assert payload["source_priority"] == "primary"
    assert "Please investigate the monitor stream." in payload["monitor_text"]
    assert "I am checking the latest pipeline." in payload["monitor_text"]
    assert "Tool use: Read" in payload["monitor_text"]
    assert "```python" in payload["monitor_text"]

    rows = _trace_rows(project)
    assert len(rows) >= 2
    assert {row["record_type"] for row in rows} >= {"user", "assistant"}
    assert all(row["session_id"] == "sess-ralph" for row in rows)


def test_monitor_ingest_uses_checkpoint_to_avoid_duplicate_refresh_spam():
    project = _make_project("checkpoint")
    transcript = project / "transcripts" / "ralph.jsonl"
    _write_transcript(
        transcript,
        [
            {
                "type": "user",
                "sessionId": "sess-ralph",
                "timestamp": "2026-04-14T10:00:00Z",
                "uuid": "u-1",
                "message": {"role": "user", "content": "Monitor the current turn."},
            },
            {
                "type": "assistant",
                "sessionId": "sess-ralph",
                "timestamp": "2026-04-14T10:00:01Z",
                "uuid": "a-1",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Initial render"}]},
            },
        ],
    )

    payload = _session_payload(session_id="sess-ralph", transcript_path=transcript)
    first = _run_hook(MONITOR_INGEST, project, payload, agent="gate-ralph")
    assert first.returncode == 0, first.stderr
    assert len(_monitor_payloads(project)) == 1
    assert len(_trace_rows(project)) == 2

    second = _run_hook(MONITOR_INGEST, project, payload, agent="gate-ralph")
    assert second.returncode == 0, second.stderr
    assert len(_monitor_payloads(project)) == 1
    assert len(_trace_rows(project)) == 2

    _append_transcript(
        transcript,
        [
            {
                "type": "assistant",
                "sessionId": "sess-ralph",
                "timestamp": "2026-04-14T10:00:05Z",
                "uuid": "a-2",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "New routed update"}]},
            }
        ],
    )
    third = _run_hook(MONITOR_INGEST, project, payload, agent="gate-ralph")
    assert third.returncode == 0, third.stderr
    assert len(_monitor_payloads(project)) == 2
    assert len(_trace_rows(project)) == 3
    assert _monitor_payloads(project)[-1]["event_count"] == 1


def test_monitor_ingest_accepts_reviewer_output_when_ralph_is_idle():
    project = _make_project("reviewer_idle", idle_seconds=60)
    ralph_transcript = project / "transcripts" / "ralph.jsonl"
    reviewer_transcript = project / "transcripts" / "architect.jsonl"
    _write_transcript(
        ralph_transcript,
        [
            {
                "type": "assistant",
                "sessionId": "sess-ralph",
                "timestamp": "2026-04-14T10:00:00Z",
                "uuid": "a-1",
                "message": {"role": "assistant", "content": [{"type": "text", "text": "Ralph is working."}]},
            }
        ],
    )
    _write_transcript(
        reviewer_transcript,
        [
            {
                "type": "assistant",
                "sessionId": "sess-architect",
                "timestamp": "2026-04-14T10:01:30Z",
                "uuid": "r-1",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Spec mismatch on the current patch."}],
                    "decision_messages": ["request changes"],
                },
            }
        ],
    )

    first = _run_hook(
        MONITOR_INGEST,
        project,
        _session_payload(session_id="sess-ralph", transcript_path=ralph_transcript),
        agent="gate-ralph",
    )
    assert first.returncode == 0, first.stderr

    second = _run_hook(
        MONITOR_INGEST,
        project,
        _session_payload(session_id="sess-architect", transcript_path=reviewer_transcript),
        agent="gate-architect",
    )
    assert second.returncode == 0, second.stderr

    payloads = _monitor_payloads(project)
    assert len(payloads) == 2
    reviewer_payload = payloads[-1]
    assert reviewer_payload["from"] == "gate-architect"
    assert reviewer_payload["source_priority"] == "secondary"
    assert reviewer_payload["route_reason"] == "primary_idle"
    assert "Spec mismatch on the current patch." in reviewer_payload["monitor_text"]


def test_install_hooks_uses_consolidated_monitor_pipeline_by_default():
    project = _make_project("inventory")
    config = json.loads((project / ".orchestrator" / "config.json").read_text(encoding="utf-8"))

    coder_inventory = build_hook_inventory(project, "gate-ralph", config)
    reviewer_inventory = build_hook_inventory(project, "gate-architect", config)

    def _commands(inventory: dict) -> list[str]:
        commands = []
        for entry in inventory["hooks"]["PostToolUse"]:
            commands.extend(hook["command"] for hook in entry.get("hooks", []))
        return commands

    coder_commands = _commands(coder_inventory)
    reviewer_commands = _commands(reviewer_inventory)

    assert any("monitor_ingest.py" in command for command in coder_commands)
    assert any("monitor_ingest.py" in command for command in reviewer_commands)
    assert all("activity_logger.py" not in command for command in coder_commands)
    assert all("activity_logger.py" not in command for command in reviewer_commands)
