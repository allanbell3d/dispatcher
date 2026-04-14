#!/usr/bin/env python3
"""Incremental Claude JSONL tailing with session-keyed checkpoint state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from lib.common import atomic_write


@dataclass(frozen=True)
class TailResult:
    records: list[dict[str, Any]]
    next_offset: int
    stopped_at_partial: bool


def _coerce_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def tail_jsonl(transcript_path: str | Path, offset: int = 0) -> TailResult:
    """Read complete JSONL records after a persisted byte offset."""
    path = _coerce_path(transcript_path)
    if not path.exists():
        return TailResult(records=[], next_offset=max(0, offset), stopped_at_partial=False)

    size = path.stat().st_size
    start = min(max(0, offset), size)
    if start >= size:
        return TailResult(records=[], next_offset=size, stopped_at_partial=False)

    data = path.read_bytes()[start:]
    if not data:
        return TailResult(records=[], next_offset=start, stopped_at_partial=False)

    records: list[dict[str, Any]] = []
    cursor = start
    stopped_at_partial = False
    lines = data.split(b"\n")

    for index, line_bytes in enumerate(lines):
        is_last_chunk = index == len(lines) - 1
        if is_last_chunk and not data.endswith(b"\n"):
            if line_bytes:
                stopped_at_partial = True
            break
        if not line_bytes:
            if is_last_chunk and data.endswith(b"\n"):
                break
            cursor += 1
            continue
        record = json.loads(line_bytes.decode("utf-8"))
        records.append(record)
        cursor += len(line_bytes) + 1

    return TailResult(records=records, next_offset=cursor, stopped_at_partial=stopped_at_partial)


def load_checkpoint_state(state_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load the checkpoint map keyed by Claude session id."""
    path = _coerce_path(state_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    sessions = raw.get("sessions") if isinstance(raw, dict) else {}
    if not isinstance(sessions, dict):
        return {}
    loaded: dict[str, dict[str, Any]] = {}
    for session_id, checkpoint in sessions.items():
        if isinstance(checkpoint, dict):
            loaded[str(session_id)] = dict(checkpoint)
    return loaded


def save_checkpoint_state(
    state_path: str | Path,
    *,
    session_id: str,
    transcript_path: str | Path,
    offset: int,
    updated_at: str | None = None,
) -> dict[str, Any]:
    """Persist checkpoint state keyed by source session."""
    path = _coerce_path(state_path)
    sessions = load_checkpoint_state(path)
    updated_at = updated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    checkpoint = {
        "session_id": session_id,
        "transcript_path": _coerce_path(transcript_path).as_posix(),
        "offset": int(offset),
        "updated_at": updated_at,
    }
    sessions[str(session_id)] = checkpoint
    payload = {"sessions": sessions}
    atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return checkpoint


if __name__ == "__main__":
    raise SystemExit(0)
