# Logging And Data Streams

## Logs

- `.orchestrator/logs/decision_trace.log`
  Hook decisions and timing. This is the most reliable low-level hook trace.
- `.orchestrator/logs/watcher.log`
  Watcher lifecycle and routing events. It is not a general per-tool activity stream.
- `.orchestrator/audit.log`
  Event-driven audit records when emitted by runtime helpers. Do not expect every tool call to appear here.
- `.orchestrator/logs/activity_<agent>.log`
  Per-agent activity summaries when `activity_logger.py` runs for a stamped agent.

## Monitor Streams

- primary: `monitor_ingest.py` writes JSON activity summaries to `dispatch/gate-monitor/inbox/`
- optional fallback: `activity_logger.py` -> `send.py` -> `watcher.py` when `session.monitor_activity_to_dispatch=true`

## Proven locally

- primary monitor stream: proven
- fallback monitor stream: proven
- watcher startup log: proven
- dispatch gate audit + trace emission: proven
- FileChanged wildcard runtime hook-engine firing: still requires one live interactive proof after install
