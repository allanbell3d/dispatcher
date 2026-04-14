#!/usr/bin/env python3
"""Parse Claude session JSONL records into a canonical monitor event model."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


_FENCE_RE = re.compile(r"```(?:[^\n`]*)\n(.*?)```", re.DOTALL)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, str):
                items.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    items.append(text)
                else:
                    items.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            else:
                items.append(str(item))
        return items
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return [text]
        return [json.dumps(value, ensure_ascii=False, sort_keys=True)]
    return [str(value)]


def _deepcopy_jsonish(value: Any) -> Any:
    return copy.deepcopy(value)


def _extract_code_blocks(text: str) -> list[str]:
    return [match.strip() for match in _FENCE_RE.findall(text) if match.strip()]


def _first_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "message", "reason"):
            item = value.get(key)
            if isinstance(item, str) and item:
                return item
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _normalize_tool_use(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "tool_use",
        "id": item.get("id", ""),
        "name": item.get("name", ""),
        "input": _deepcopy_jsonish(item.get("input")),
    }


def _normalize_tool_result(item: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": item.get("tool_use_id", ""),
        "name": item.get("name", ""),
        "is_error": bool(item.get("is_error", False)),
        "content": _deepcopy_jsonish(item.get("content")),
    }
    if "error" in item:
        result["error"] = _deepcopy_jsonish(item["error"])
    return result


def _normalize_block(block: Any) -> dict[str, Any]:
    if isinstance(block, str):
        return {"type": "text", "text": block}
    if not isinstance(block, dict):
        return {"type": "text", "text": str(block)}

    kind = str(block.get("type") or block.get("kind") or block.get("role") or "text")
    if kind == "tool_use":
        return _normalize_tool_use(block)
    if kind == "tool_result":
        return _normalize_tool_result(block)
    if kind == "thinking":
        return {
            "type": "thinking",
            "text": block.get("text", block.get("content", "")),
        }

    normalized = _deepcopy_jsonish(block)
    normalized["type"] = kind
    if "text" not in normalized and isinstance(normalized.get("content"), str):
        normalized["text"] = normalized["content"]
    if "text" not in normalized and kind == "text":
        normalized["text"] = ""
    return normalized


def _resolve_record(raw: dict[str, Any]) -> dict[str, Any]:
    record = _deepcopy_jsonish(raw)
    message = record.get("message")
    if isinstance(message, dict):
        for key in ("role", "content", "text", "tool_calls", "decision_messages", "warning_messages"):
            if key not in record and key in message:
                record[key] = _deepcopy_jsonish(message[key])
    return record


def _normalize_text_and_blocks(record: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    content = record.get("content")
    if content is None and "text" in record:
        content = record.get("text")

    blocks: list[dict[str, Any]] = []
    text_blocks: list[str] = []
    code_blocks: list[str] = []
    tool_uses: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []

    if content is None:
        return text_blocks, code_blocks, blocks, tool_uses, tool_results

    items = content if isinstance(content, list) else [content]
    for item in items:
        block = _normalize_block(item)
        blocks.append(block)
        block_type = block.get("type", "text")
        if block_type == "tool_use":
            tool_uses.append(block)
            continue
        if block_type == "tool_result":
            tool_results.append(block)
            continue
        if block_type == "thinking":
            continue

        text = block.get("text")
        if isinstance(text, str) and text:
            text_blocks.append(text)
            code_blocks.extend(_extract_code_blocks(text))

    return text_blocks, code_blocks, blocks, tool_uses, tool_results


@dataclass(slots=True)
class ParsedSessionEvent:
    session_id: str = ""
    source_agent: str = ""
    source_role: str = ""
    source_kind: str = ""
    timestamp: str = ""
    uuid: str = ""
    parent_uuid: str = ""
    record_type: str = ""
    subtype: str = ""
    cwd: str = ""
    git_branch: str = ""
    text_blocks: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    tool_uses: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    decision_messages: list[str] = field(default_factory=list)
    warning_messages: list[str] = field(default_factory=list)
    content_blocks: list[dict[str, Any]] = field(default_factory=list)
    raw_content: dict[str, Any] = field(default_factory=dict)

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source_agent": self.source_agent,
            "source_role": self.source_role,
            "source_kind": self.source_kind,
            "timestamp": self.timestamp,
            "uuid": self.uuid,
            "parent_uuid": self.parent_uuid,
            "record_type": self.record_type,
            "subtype": self.subtype,
            "cwd": self.cwd,
            "git_branch": self.git_branch,
            "text_blocks": _deepcopy_jsonish(self.text_blocks),
            "code_blocks": _deepcopy_jsonish(self.code_blocks),
            "tool_uses": _deepcopy_jsonish(self.tool_uses),
            "tool_results": _deepcopy_jsonish(self.tool_results),
            "decision_messages": _deepcopy_jsonish(self.decision_messages),
            "warning_messages": _deepcopy_jsonish(self.warning_messages),
            "content_blocks": _deepcopy_jsonish(self.content_blocks),
            "raw_content": _deepcopy_jsonish(self.raw_content),
        }


def parse_session_record(raw: dict[str, Any]) -> ParsedSessionEvent:
    record = _resolve_record(raw)

    session_id = str(
        record.get("session_id")
        or record.get("sessionId")
        or record.get("conversation_id")
        or ""
    )
    record_type = str(record.get("type") or record.get("record_type") or record.get("kind") or "")
    source_role = str(record.get("source_role") or record.get("role") or (record_type if record_type in {"user", "assistant", "system"} else ""))
    source_kind = str(record.get("source_kind") or record.get("kind") or record_type or "")

    text_blocks, code_blocks, content_blocks, tool_uses, tool_results = _normalize_text_and_blocks(record)
    decisions = _string_list(record.get("decision_messages") or record.get("decisions") or record.get("decision"))
    warnings = _string_list(record.get("warning_messages") or record.get("warnings") or record.get("warning"))

    if record_type == "permission-mode" and not decisions:
        decisions = _string_list(record.get("subtype") or record.get("mode"))
    return ParsedSessionEvent(
        session_id=session_id,
        source_agent=str(record.get("source_agent") or record.get("agent") or record.get("author") or source_role or ""),
        source_role=source_role,
        source_kind=source_kind,
        timestamp=str(record.get("timestamp") or record.get("ts") or ""),
        uuid=str(record.get("uuid") or record.get("id") or ""),
        parent_uuid=str(record.get("parent_uuid") or record.get("parentId") or record.get("parent_id") or ""),
        record_type=record_type,
        subtype=str(record.get("subtype") or record.get("name") or record.get("mode") or ""),
        cwd=str(record.get("cwd") or ""),
        git_branch=str(record.get("git_branch") or record.get("branch") or ""),
        text_blocks=text_blocks,
        code_blocks=code_blocks,
        tool_uses=tool_uses,
        tool_results=tool_results,
        decision_messages=decisions,
        warning_messages=warnings,
        content_blocks=content_blocks,
        raw_content=_deepcopy_jsonish(record),
    )


def parse_session_jsonl_text(text: str) -> list[ParsedSessionEvent]:
    lines = [line for line in text.splitlines() if line.strip()]
    events: list[ParsedSessionEvent] = []
    for index, line in enumerate(lines):
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                break
            raise
        if isinstance(raw, dict):
            events.append(parse_session_record(raw))
    return events


def parse_session_jsonl_file(path: str | Path) -> list[ParsedSessionEvent]:
    return parse_session_jsonl_text(Path(path).read_text(encoding="utf-8"))


def event_to_trace_payload(event: ParsedSessionEvent) -> dict[str, Any]:
    return event.to_trace_dict()


def event_to_trace_json(event: ParsedSessionEvent) -> str:
    return json.dumps(event.to_trace_dict(), ensure_ascii=False, sort_keys=True)
