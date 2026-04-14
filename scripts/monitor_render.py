#!/usr/bin/env python3
"""Render canonical monitor events as trace or monitor output."""

from __future__ import annotations

import json
from typing import Any

try:
    from scripts.monitor_parse import ParsedSessionEvent
except ImportError:  # pragma: no cover - direct script import path
    from monitor_parse import ParsedSessionEvent


_SUPPRESSED_RECORD_TYPES = {"file-history-snapshot"}


def render_trace_event(event: ParsedSessionEvent) -> str:
    return json.dumps(event.to_trace_dict(), ensure_ascii=False, sort_keys=True)


def _title_for_event(event: ParsedSessionEvent) -> str:
    if event.source_role in {"user", "assistant", "system"}:
        return event.source_role.title()
    if event.record_type:
        return event.record_type.replace("-", " ").title()
    if event.source_kind:
        return event.source_kind.replace("-", " ").title()
    return "Event"


def _render_tool_use(block: dict[str, Any]) -> list[str]:
    lines = [f"Tool use: {block.get('name', '')}".rstrip()]
    tool_input = block.get("input")
    if tool_input is not None:
        lines.append(f"Input: {json.dumps(tool_input, ensure_ascii=False, sort_keys=True)}")
    return lines


def _render_tool_result(block: dict[str, Any]) -> list[str]:
    label = f"Tool result: {block.get('name', '')}".rstrip()
    if block.get("is_error"):
        label += " (error)"
    lines = [label]
    content = block.get("content")
    if content is not None:
        if isinstance(content, str):
            lines.append(content)
        else:
            lines.append(json.dumps(content, ensure_ascii=False, sort_keys=True))
    error = block.get("error")
    if error and error not in lines[-1:]:
        lines.append(str(error))
    return lines


def _render_block(block: dict[str, Any]) -> list[str]:
    block_type = block.get("type", "text")
    if block_type == "thinking":
        return []
    if block_type == "tool_use":
        return _render_tool_use(block)
    if block_type == "tool_result":
        return _render_tool_result(block)
    text = block.get("text")
    if isinstance(text, str) and text.strip():
        return [text]
    return []


def render_monitor_event(event: ParsedSessionEvent) -> str:
    if event.record_type in _SUPPRESSED_RECORD_TYPES:
        return ""
    if event.record_type == "queue-operation" and not (event.decision_messages or event.warning_messages):
        return ""

    lines: list[str] = []
    title = _title_for_event(event)
    if event.text_blocks or event.tool_uses or event.tool_results:
        lines.append(f"{title}:")

    for block in event.content_blocks:
        rendered = _render_block(block)
        if rendered:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(rendered)

    for message in event.decision_messages:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"Decision: {message}")

    for message in event.warning_messages:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"Warning: {message}")

    return "\n".join(lines).strip()
