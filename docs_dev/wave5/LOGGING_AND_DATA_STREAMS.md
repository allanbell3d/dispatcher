# Logging And Data Streams

## Logs

- `.orchestrator/logs/monitor_trace.jsonl`
  Durable structured event trace for the consolidated monitor pipeline. This is the human-usable trace that is generated from parsed Claude session JSONL events.
- `.orchestrator/logs/decision_trace.log`
  Hook decisions and timing. This remains the low-level hook trace.
- `.orchestrator/logs/watcher.log`
  Watcher lifecycle and routing events. It is not a general per-tool activity stream.
- `.orchestrator/audit.log`
  Event-driven audit records when emitted by runtime helpers. Do not expect every tool call to appear here.
- `.orchestrator/logs/activity_<agent>.log`
  Legacy per-agent summaries from `activity_logger.py`. This is no longer the default installed monitor path.

## Pipeline State

- `.orchestrator/runtime_flags/monitor_tail_state.json`
  Session-keyed checkpoint state for transcript offsets.
- `.orchestrator/runtime_flags/monitor_route_state.json`
  Last primary-source timestamp used to decide when reviewer output should surface while Ralph is idle.

## Monitor Streams

- default installed path: `monitor_ingest.py`
  Triggered from PostToolUse, but the actual source input is Claude session JSONL, not the hook payload summary.
- source of truth: Claude session transcripts in `C:\Users\<user>\.claude\projects\<project-slug>\<session-id>.jsonl`
- render path:
  1. incremental tail with offset checkpoint
  2. full parse into canonical event records
  3. trace render to `monitor_trace.jsonl`
  4. monitor render written as JSON payloads to `dispatch/gate-monitor/inbox/`
- reviewer handling:
  - `gate-ralph` is primary live source
  - reviewer sessions are secondary monitor inputs
  - reviewer output is surfaced when Ralph is idle, or when the reviewer event carries meaningful decision/warning signal
- legacy/manual path: `activity_logger.py` can still emit local activity summaries and optional fallback dispatch mail, but it is no longer installed by default for the live monitor stream

## Proven locally

- checkpointed JSONL tailer: proven
- canonical parser + dual renderers: proven
- primary monitor stream from session JSONL: proven
- reviewer-as-secondary monitor routing when Ralph is idle: proven
- durable monitor trace logging: proven
- legacy `activity_logger.py` fallback behavior: still works when invoked directly
- watcher startup log: proven
- dispatch gate audit + trace emission: proven
- FileChanged wildcard runtime hook-engine firing: still requires one live interactive proof after install
