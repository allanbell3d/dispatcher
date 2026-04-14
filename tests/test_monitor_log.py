import json
import shutil
import uuid
from pathlib import Path

from scripts.monitor_log import DurableTraceWriter


def _event(uuid: str | None = None, **overrides):
    event = {
        "timestamp": "2026-04-14T12:00:00+00:00",
        "session_id": "session-1",
        "source_agent": "gate-ralph",
        "event_type": "assistant",
        "uuid": "" if uuid is None else uuid,
        "tool_name": "Bash",
        "decision_messages": ["Proceed with routing"],
        "warning_messages": [],
        "monitor_text": "```python\nprint('hello')\n```",
        "raw_content": "Bearer abcdefghijklmnopqrstuvwxyz0123456789",
    }
    event.update(overrides)
    return event


def _read_jsonl(path: Path):
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _make_tmp_dir() -> Path:
    base = Path.cwd() / "scratch_log_test"
    path = base / f"monitor-log-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def test_trace_writer_emits_one_structured_entry_per_event():
    tmp_dir = _make_tmp_dir()
    try:
        log_path = tmp_dir / "monitor_trace.jsonl"
        writer = DurableTraceWriter(log_path)

        writer.write(_event("evt-1"))

        rows = _read_jsonl(log_path)
        assert len(rows) == 1
        assert rows[0]["session_id"] == "session-1"
        assert rows[0]["source_agent"] == "gate-ralph"
        assert rows[0]["event_type"] == "assistant"
        assert rows[0]["uuid"] == "evt-1"
        assert rows[0]["raw_content"] == "Bearer ***REDACTED***"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_trace_writer_truncates_noisy_payloads():
    tmp_dir = _make_tmp_dir()
    try:
        log_path = tmp_dir / "monitor_trace.jsonl"
        writer = DurableTraceWriter(log_path, max_field_chars=64)

        writer.write(_event("evt-2", raw_content="x" * 300, monitor_text="y" * 300))

        rows = _read_jsonl(log_path)
        assert rows[0]["raw_content"].endswith("...[+236]")
        assert rows[0]["monitor_text"].endswith("...[+236]")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_trace_writer_skips_duplicate_unchanged_events():
    tmp_dir = _make_tmp_dir()
    try:
        log_path = tmp_dir / "monitor_trace.jsonl"
        writer = DurableTraceWriter(log_path)
        event = _event("", event_type="system", subtype="turn_duration")

        writer.write(event)
        writer.write(dict(event))

        rows = _read_jsonl(log_path)
        assert len(rows) == 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_trace_writer_rotates_when_file_exceeds_limit():
    tmp_dir = _make_tmp_dir()
    try:
        log_path = tmp_dir / "monitor_trace.jsonl"
        writer = DurableTraceWriter(log_path, max_bytes=220, backup_count=2)

        writer.write(_event("evt-4", raw_content="a" * 150))
        writer.write(_event("evt-5", raw_content="b" * 150))

        assert log_path.exists()
        assert (tmp_dir / "monitor_trace.jsonl.1").exists()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
