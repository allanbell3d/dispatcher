#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

"""Consolidated monitor/logging pipeline trigger for Claude session JSONL."""
import json
import os
import time as _time
from datetime import datetime
from pathlib import Path

from lib.common import (
    atomic_write,
    file_stamp,
    hook_input,
    load_project_config,
    resolve_path,
    resolve_project_root,
    timestamp,
    trace_hook,
)
from scripts.monitor_log import DurableTraceWriter
from scripts.monitor_parse import parse_session_record
from scripts.monitor_render import render_monitor_event
from scripts.monitor_route import MonitorRouter
from scripts.monitor_tail import load_checkpoint_state, save_checkpoint_state, tail_jsonl


OK = {}
COMMAND_MATCHER_TOOLS = {"Bash", "Write", "Edit", "MultiEdit", "Read", "Grep", "Glob"}
CHECKPOINT_FILE = "monitor_tail_state.json"
ROUTE_STATE_FILE = "monitor_route_state.json"
TRACE_LOG_FILE = "monitor_trace.jsonl"


def _log_stderr(msg: str) -> None:
    try:
        print(f"[monitor_ingest] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _agent_roles(config: dict, agent_name: str) -> set[str]:
    for a in config.get("agents", []):
        if a.get("name") == agent_name:
            return {str(role) for role in (a.get("roles") or []) if str(role)}
    return set()


def _monitor_source_role(roles: set[str]) -> str:
    if "coder" in roles:
        return "coder"
    if "reviewer" in roles:
        return "reviewer"
    return ""


def _project_slug(project_root: Path) -> str:
    return str(project_root).replace(":", "-").replace("\\", "-").replace("/", "-")


def _session_id_from_payload(payload: dict) -> str:
    return str(payload.get("session_id") or payload.get("sessionId") or "").strip()


def _resolve_transcript_path(project_root: Path, payload: dict) -> Path | None:
    transcript_path = str(payload.get("transcript_path") or payload.get("transcriptPath") or "").strip()
    if transcript_path:
        candidate = Path(transcript_path)
        if candidate.exists():
            return candidate

    session_id = _session_id_from_payload(payload)
    if not session_id:
        return None

    candidate = Path.home() / ".claude" / "projects" / _project_slug(project_root) / f"{session_id}.jsonl"
    if candidate.exists():
        return candidate
    return None


def _load_route_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_route_state(path: Path, *, last_primary_event_at: datetime | None) -> None:
    payload = {
        "last_primary_event_at": last_primary_event_at.isoformat() if last_primary_event_at else "",
    }
    atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _hydrate_router(project_root: Path, config: dict) -> tuple[MonitorRouter, Path]:
    state_path = resolve_path("runtime_flags", project_root, config) / ROUTE_STATE_FILE
    router = MonitorRouter(
        monitor_targets=config.get("routing", {}).get("cc_all", []),
        primary_agents={"gate-ralph"},
        idle_seconds=int(config.get("wake", {}).get("idle_threshold_seconds", 120)),
    )
    state = _load_route_state(state_path)
    stamp = state.get("last_primary_event_at")
    if isinstance(stamp, str) and stamp:
        try:
            router.last_primary_event_at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            router.last_primary_event_at = None
    return router, state_path


def _aggregate_monitor_text(chunks: list[str]) -> str:
    return "\n\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip()).strip()


def main() -> int:
    agent = os.environ.get("GATE_AGENT_NAME", "").strip()
    if not agent:
        print(json.dumps(OK))
        return 0

    from lib.common import is_hook_disabled
    if is_hook_disabled("monitor_ingest"):
        print(json.dumps(OK))
        return 0

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        print(json.dumps(OK))
        return 0

    _t0 = _time.monotonic()

    tool_name, tool_input, tool_response, exit_code = hook_input(payload)
    if tool_name not in COMMAND_MATCHER_TOOLS:
        trace_hook(hook="monitor_ingest", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="tool not matched")
        print(json.dumps(OK))
        return 0

    try:
        project_root = resolve_project_root()
        config = load_project_config(project_root)
        dispatch_root = resolve_path("dispatch_root", project_root, config)
    except Exception as exc:
        _log_stderr(f"config load failed: {exc}")
        print(json.dumps(OK))
        return 0

    agent_roles = _agent_roles(config, agent)
    monitor_source_role = _monitor_source_role(agent_roles)
    if not monitor_source_role:
        trace_hook(hook="monitor_ingest", agent=agent, decision="skip",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="unsupported agent role")
        print(json.dumps(OK))
        return 0

    transcript_path = _resolve_transcript_path(project_root, payload)
    session_id = _session_id_from_payload(payload)
    if transcript_path is None:
        trace_hook(hook="monitor_ingest", agent=agent, decision="skip",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   reason="transcript unavailable")
        print(json.dumps(OK))
        return 0

    runtime_flags_dir = resolve_path("runtime_flags", project_root, config)
    logs_dir = resolve_path("logs", project_root, config)
    checkpoint_path = runtime_flags_dir / CHECKPOINT_FILE
    checkpoints = load_checkpoint_state(checkpoint_path)
    checkpoint = checkpoints.get(session_id, {}) if session_id else {}
    offset = int(checkpoint.get("offset", 0)) if checkpoint else 0

    tail_result = tail_jsonl(transcript_path, offset=offset)
    if session_id:
        save_checkpoint_state(
            checkpoint_path,
            session_id=session_id,
            transcript_path=transcript_path,
            offset=tail_result.next_offset,
        )

    if not tail_result.records:
        trace_hook(hook="monitor_ingest", agent=agent, decision="skip",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   project_root=project_root, config=config,
                   session_id=session_id, reason="no new session records")
        print(json.dumps(OK))
        return 0

    trace_writer = DurableTraceWriter(logs_dir / TRACE_LOG_FILE)
    router, route_state_path = _hydrate_router(project_root, config)

    delivered_monitor_chunks: list[str] = []
    recipients: set[str] = set()
    source_priority = ""
    route_reason = ""
    delivered_events = 0

    for raw_record in tail_result.records:
        event = parse_session_record(raw_record)
        trace_payload = event.to_trace_dict()
        trace_payload["session_id"] = session_id or event.session_id
        trace_payload["source_agent"] = agent
        trace_payload["source_role"] = monitor_source_role
        trace_payload["session_role"] = event.source_role
        trace_payload["source_kind"] = "session_jsonl"
        trace_payload["event_type"] = event.record_type
        trace_payload["tool"] = tool_name
        trace_payload["exit_code"] = exit_code

        monitor_text = render_monitor_event(event)
        trace_payload["monitor_text"] = monitor_text
        trace_writer.write(trace_payload)

        decision = router.route_event(
            {
                "session_id": trace_payload["session_id"],
                "source_agent": agent,
                "source_role": monitor_source_role,
                "timestamp": trace_payload["timestamp"],
                "record_type": trace_payload["record_type"],
                "monitor_text": monitor_text,
                "decision_messages": trace_payload.get("decision_messages", []),
                "warning_messages": trace_payload.get("warning_messages", []),
            }
        )
        if decision.deliver and monitor_text:
            delivered_events += 1
            delivered_monitor_chunks.append(monitor_text)
            recipients.update(decision.recipients)
            source_priority = decision.source_priority
            route_reason = decision.reason

    _save_route_state(route_state_path, last_primary_event_at=router.last_primary_event_at)

    if delivered_events:
        body = json.dumps(
            {
                "ts": timestamp(config),
                "from": agent,
                "tool": tool_name,
                "exit_code": exit_code,
                "session_id": session_id,
                "source_priority": source_priority,
                "route_reason": route_reason,
                "event_count": delivered_events,
                "trace_log": str(logs_dir / TRACE_LOG_FILE),
                "monitor_text": _aggregate_monitor_text(delivered_monitor_chunks),
            },
            ensure_ascii=False,
            indent=2,
        )

        fs = file_stamp(config)
        safe_tool = tool_name.replace("/", "_").replace("\\", "_")
        filename = f"{fs}-{agent}-{safe_tool}.json"
        for recipient in recipients:
            if recipient == agent:
                continue
            inbox = dispatch_root / recipient / "inbox"
            try:
                inbox.mkdir(parents=True, exist_ok=True)
                atomic_write(inbox / filename, body)
            except OSError as exc:
                _log_stderr(f"write to {recipient}/inbox failed: {exc}")

    trace_hook(hook="monitor_ingest", agent=agent, decision="allow",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               tool=tool_name, recipients=sorted(recipients),
               event_count=len(tail_result.records), delivered_events=delivered_events,
               session_id=session_id)
    print(json.dumps(OK))
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # P4: advisory — fail-open
