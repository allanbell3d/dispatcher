import json
from pathlib import Path

from scripts.monitor_tail import (
    load_checkpoint_state,
    save_checkpoint_state,
    tail_jsonl,
)


def _line(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"


def test_tail_jsonl_starts_from_byte_offset():
    transcript = Path("transcript.jsonl")
    try:
        line1 = _line({"seq": 1, "text": "alpha"})
        line2 = _line({"seq": 2, "text": "beta"})
        line3 = _line({"seq": 3, "text": "gamma"})
        transcript.write_bytes(line1 + line2 + line3)

        result = tail_jsonl(transcript, offset=len(line1))

        assert [record["seq"] for record in result.records] == [2, 3]
        assert result.next_offset == len(line1) + len(line2) + len(line3)
        assert result.stopped_at_partial is False
    finally:
        transcript.unlink(missing_ok=True)


def test_tail_jsonl_stops_before_partial_last_line():
    transcript = Path("transcript.jsonl")
    try:
        first = _line({"seq": 1, "text": "alpha"})
        second = _line({"seq": 2, "text": "beta"})
        partial = b'{"seq":3,"text":"incomplete'
        transcript.write_bytes(first + second + partial)

        result = tail_jsonl(transcript, offset=0)

        assert [record["seq"] for record in result.records] == [1, 2]
        assert result.next_offset == len(first) + len(second)
        assert result.stopped_at_partial is True

        transcript.write_bytes(first + second + partial + b'"}\n')
        resumed = tail_jsonl(transcript, offset=result.next_offset)

        assert [record["seq"] for record in resumed.records] == [3]
        assert resumed.next_offset == transcript.stat().st_size
        assert resumed.stopped_at_partial is False
    finally:
        transcript.unlink(missing_ok=True)


def test_checkpoint_state_is_keyed_by_session_and_preserves_offset():
    state_path = Path("monitor_tail_state.json")
    try:
        save_checkpoint_state(
            state_path,
            session_id="session-a",
            transcript_path=Path("C:/claude/session-a.jsonl"),
            offset=120,
            updated_at="2026-04-14T10:00:00Z",
        )
        save_checkpoint_state(
            state_path,
            session_id="session-b",
            transcript_path=Path("C:/claude/session-b.jsonl"),
            offset=88,
            updated_at="2026-04-14T10:05:00Z",
        )

        raw = json.loads(state_path.read_text(encoding="utf-8"))
        assert set(raw["sessions"]) == {"session-a", "session-b"}
        assert raw["sessions"]["session-a"]["transcript_path"] == "C:/claude/session-a.jsonl"
        assert raw["sessions"]["session-a"]["offset"] == 120
        assert raw["sessions"]["session-a"]["updated_at"] == "2026-04-14T10:00:00Z"

        state = load_checkpoint_state(state_path)
        assert state["session-a"]["session_id"] == "session-a"
        assert state["session-a"]["transcript_path"] == "C:/claude/session-a.jsonl"
        assert state["session-a"]["offset"] == 120
        assert state["session-b"]["updated_at"] == "2026-04-14T10:05:00Z"
    finally:
        state_path.unlink(missing_ok=True)
