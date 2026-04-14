import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import monitor_parse
import monitor_render


def test_render_trace_and_monitor_outputs_from_same_parsed_event():
    event = monitor_parse.parse_session_record(
        {
            "session_id": "sess-123",
            "uuid": "u-1",
            "parent_uuid": "u-0",
            "timestamp": "2026-04-14T10:00:00Z",
            "source_agent": "gate-ralph",
            "source_role": "assistant",
            "source_kind": "assistant",
            "type": "assistant",
            "subtype": "message",
            "cwd": "D:\\IA\\dispatcher_repo",
            "git_branch": "dev",
            "content": [
                {"type": "text", "text": "Here is the patch:\n```python\nprint('hello')\n```"},
                {"type": "thinking", "text": "Inspect the parser before changing it."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "Read",
                    "input": {"file_path": "scripts/monitor_parse.py"},
                },
            ],
        }
    )

    trace = monitor_render.render_trace_event(event)
    trace_data = json.loads(trace)

    assert trace_data["session_id"] == "sess-123"
    assert trace_data["uuid"] == "u-1"
    assert trace_data["timestamp"] == "2026-04-14T10:00:00Z"
    assert trace_data["tool_uses"] == [
        {
            "type": "tool_use",
            "id": "toolu_1",
            "name": "Read",
            "input": {"file_path": "scripts/monitor_parse.py"},
        }
    ]
    assert trace_data["raw_content"]["uuid"] == "u-1"

    monitor = monitor_render.render_monitor_event(event)

    assert "sess-123" not in monitor
    assert "u-1" not in monitor
    assert "2026-04-14T10:00:00Z" not in monitor
    assert "Here is the patch:" in monitor
    assert "```python" in monitor
    assert "print('hello')" in monitor
    assert "Tool use: Read" in monitor


def test_render_monitor_keeps_decisions_and_warnings_but_strips_snapshot_noise():
    decision_event = monitor_parse.parse_session_record(
        {
            "session_id": "sess-123",
            "uuid": "u-2",
            "timestamp": "2026-04-14T10:01:00Z",
            "source_agent": "gate-monitor",
            "source_role": "user",
            "source_kind": "user",
            "type": "user",
            "subtype": "prompt",
            "content": [
                {"type": "text", "text": "Please review the output."},
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_1",
                    "name": "Read",
                    "is_error": True,
                    "content": {
                        "error": "file not found",
                        "path": "scripts/monitor_parse.py",
                    },
                },
            ],
            "decision_messages": ["pause"],
            "warning_messages": ["tool failed"],
        }
    )
    snapshot_event = monitor_parse.parse_session_record(
        {
            "session_id": "sess-123",
            "uuid": "u-3",
            "timestamp": "2026-04-14T10:02:00Z",
            "source_agent": "system",
            "source_role": "system",
            "source_kind": "system",
            "type": "file-history-snapshot",
            "content": [{"type": "text", "text": "Current file history snapshot."}],
        }
    )
    queue_event = monitor_parse.parse_session_record(
        {
            "session_id": "sess-123",
            "uuid": "u-4",
            "timestamp": "2026-04-14T10:03:00Z",
            "source_agent": "gate-monitor",
            "source_role": "system",
            "source_kind": "system",
            "type": "queue-operation",
            "subtype": "enqueue",
            "content": [{"type": "text", "text": "Queued for the next turn."}],
        }
    )

    monitor = monitor_render.render_monitor_event(decision_event)
    assert "Please review the output." in monitor
    assert "Tool result: Read" in monitor
    assert "file not found" in monitor
    assert "pause" in monitor
    assert "tool failed" in monitor

    assert monitor_render.render_monitor_event(snapshot_event).strip() == ""
    assert monitor_render.render_monitor_event(queue_event).strip() == ""
