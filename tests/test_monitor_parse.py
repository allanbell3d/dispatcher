import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import monitor_parse


def _jsonl(records: list[dict], *, tail: str = "") -> str:
    payload = "\n".join(json.dumps(record) for record in records)
    if tail:
        payload += "\n" + tail
    return payload


def test_parse_session_jsonl_text_preserves_all_record_shapes_and_stops_on_partial_final_line():
    records = [
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
        },
        {
            "session_id": "sess-123",
            "uuid": "u-2",
            "parent_uuid": "u-1",
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
        },
        {
            "session_id": "sess-123",
            "uuid": "u-3",
            "timestamp": "2026-04-14T10:02:00Z",
            "source_agent": "system",
            "source_role": "system",
            "source_kind": "system",
            "type": "permission-mode",
            "subtype": "read-only",
            "content": [{"type": "text", "text": "Permission mode set to read-only."}],
        },
        {
            "session_id": "sess-123",
            "uuid": "u-4",
            "timestamp": "2026-04-14T10:03:00Z",
            "source_agent": "system",
            "source_role": "system",
            "source_kind": "system",
            "type": "file-history-snapshot",
            "content": [{"type": "text", "text": "Current file history snapshot."}],
        },
        {
            "session_id": "sess-123",
            "uuid": "u-5",
            "timestamp": "2026-04-14T10:04:00Z",
            "source_agent": "gate-monitor",
            "source_role": "assistant",
            "source_kind": "assistant",
            "type": "attachment",
            "content": [{"type": "text", "text": "Attached context for the next turn."}],
        },
        {
            "session_id": "sess-123",
            "uuid": "u-6",
            "timestamp": "2026-04-14T10:05:00Z",
            "source_agent": "gate-monitor",
            "source_role": "system",
            "source_kind": "system",
            "type": "queue-operation",
            "subtype": "enqueue",
            "content": [{"type": "text", "text": "Queued for the next turn."}],
        },
    ]

    text = _jsonl(records, tail='{"session_id": "sess-123", "uuid": "u-7"')

    events = monitor_parse.parse_session_jsonl_text(text)

    assert len(events) == 6

    assistant = events[0]
    assert assistant.session_id == "sess-123"
    assert assistant.source_agent == "gate-ralph"
    assert assistant.source_role == "assistant"
    assert assistant.source_kind == "assistant"
    assert assistant.record_type == "assistant"
    assert assistant.subtype == "message"
    assert assistant.text_blocks == ["Here is the patch:\n```python\nprint('hello')\n```"]
    assert assistant.code_blocks == ["print('hello')"]
    assert assistant.tool_uses == [
        {
            "type": "tool_use",
            "id": "toolu_1",
            "name": "Read",
            "input": {"file_path": "scripts/monitor_parse.py"},
        }
    ]
    assert assistant.content_blocks[1]["type"] == "thinking"
    assert assistant.raw_content["uuid"] == "u-1"

    user = events[1]
    assert user.record_type == "user"
    assert user.text_blocks == ["Please review the output."]
    assert user.tool_results == [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_1",
            "name": "Read",
            "is_error": True,
            "content": {
                "error": "file not found",
                "path": "scripts/monitor_parse.py",
            },
        }
    ]
    assert user.decision_messages == ["pause"]
    assert user.warning_messages == ["tool failed"]

    assert [event.record_type for event in events[2:]] == [
        "permission-mode",
        "file-history-snapshot",
        "attachment",
        "queue-operation",
    ]
    assert events[2].subtype == "read-only"
    assert events[3].text_blocks == ["Current file history snapshot."]
    assert events[4].text_blocks == ["Attached context for the next turn."]
    assert events[5].subtype == "enqueue"
