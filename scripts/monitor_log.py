#!/usr/bin/env python3
"""Durable trace writer for consolidated monitor events."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


SECRET_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"), "Bearer ***REDACTED***"),
    (re.compile(r"sk-[A-Za-z0-9]{10,}"), "sk-***REDACTED***"),
    (re.compile(r"rt_[A-Za-z0-9\-]{10,}"), "rt_***REDACTED***"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AKIA***REDACTED***"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "gh***REDACTED***"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "github_pat_***REDACTED***"),
    (re.compile(r"\bxox[a-z]-[A-Za-z0-9-]{10,}\b"), "xox***REDACTED***"),
]


def _redact_text(text: str) -> str:
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


class DurableTraceWriter:
    """Append structured JSONL monitor-trace rows with dedupe and rotation."""

    def __init__(
        self,
        log_path: str | Path,
        *,
        max_field_chars: int = 2048,
        max_bytes: int | None = None,
        backup_count: int = 3,
    ) -> None:
        self.log_path = Path(log_path)
        self.max_field_chars = max(32, max_field_chars)
        self.max_bytes = max_bytes
        self.backup_count = max(0, backup_count)
        self._last_signature: str | None = None

    def write(self, event: dict[str, Any]) -> bool:
        record = self._sanitize_value(event)
        signature = self._signature(record)
        if signature == self._last_signature:
            return False

        encoded = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if self.max_bytes is not None and self.log_path.exists():
            if self.log_path.stat().st_size + len(encoded) > self.max_bytes:
                self._rotate()

        with self.log_path.open("ab") as handle:
            handle.write(encoded)

        self._last_signature = signature
        return True

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, str):
            return self._truncate_text(_redact_text(value))
        return value

    def _truncate_text(self, value: str) -> str:
        if len(value) <= self.max_field_chars:
            return value
        extra = len(value) - self.max_field_chars
        return value[: self.max_field_chars] + f"...[+{extra}]"

    def _signature(self, record: dict[str, Any]) -> str:
        session_id = str(record.get("session_id") or "")
        event_uuid = str(record.get("uuid") or "")
        if event_uuid:
            return f"{session_id}:{event_uuid}"
        stable = {key: value for key, value in record.items() if key != "timestamp"}
        digest = hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return f"{session_id}:{digest}"

    def _rotate(self) -> None:
        if self.backup_count <= 0 or not self.log_path.exists():
            self.log_path.unlink(missing_ok=True)
            return

        oldest = self.log_path.with_name(f"{self.log_path.name}.{self.backup_count}")
        oldest.unlink(missing_ok=True)
        for index in range(self.backup_count - 1, 0, -1):
            source = self.log_path.with_name(f"{self.log_path.name}.{index}")
            target = self.log_path.with_name(f"{self.log_path.name}.{index + 1}")
            if source.exists():
                source.replace(target)
        self.log_path.replace(self.log_path.with_name(f"{self.log_path.name}.1"))
