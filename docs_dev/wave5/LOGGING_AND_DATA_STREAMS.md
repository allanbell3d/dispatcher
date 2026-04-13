# Logging And Data Streams

Wave 5 depends on a few clear streams. If you know which stream carries which kind of truth, debugging gets much easier.

## Primary Streams

| Stream | Path | What It Means | Who Writes |
|---|---|---|---|
| Decision trace | `.orchestrator/logs/decision_trace.log` | Hook decisions, allow/deny/skip, and timing | `trace_hook()` |
| Audit log | `.orchestrator/audit.log` | Durable operator and watcher events | `audit_log()` |
| Watcher log | `.orchestrator/logs/watcher.log` | Delivery, wake, fan-in, and error behavior | `scripts/watcher.py` |
| Activity log | `.orchestrator/logs/activity_<agent>.log` | Per-agent tool activity summary | `hooks/activity_logger.py` |
| Monitor inbox | `dispatch/gate-monitor/inbox/` | Live summarized activity for `gate-monitor` | watcher and `monitor_ingest.py` |
| Verdict store | `.orchestrator/merged_verdicts/<task_id>.json` | Commit-gate result for the current task | watcher |

## How To Read Them

- Use the decision trace when a hook allowed, blocked, or skipped something and you need to know why.
- Use the audit log when the operator or watcher made a durable state change.
- Use the watcher log when mail delivery, wake behavior, or verdict fan-in looks wrong.
- Use the activity log when you need a per-agent summary of what the tool call did.
- Use the monitor inbox when you want to know what `gate-monitor` was actually told.

## Stream Boundaries

- Decision trace is for decisions, not full payload history.
- Audit log is for durable events, not a replacement for message files.
- Watcher log is a run log, not a communication bus.
- Inbox files are communication, not audit history.
- `merged_verdicts` is a single-writer output, not a scratchpad.

## Common Checks

1. If a hook seems silent, check `.orchestrator/logs/decision_trace.log` first.
2. If a message never arrived, check `.orchestrator/logs/watcher.log` next.
3. If the monitor saw nothing, check `dispatch/gate-monitor/inbox/`.
4. If commit gating blocks, check `.orchestrator/merged_verdicts/<task_id>.json`.
5. If the operator changed the flow manually, record it in `WAVE5_RESULTS_TEMPLATE.md`.

## Practical Rule

When the logs disagree, trust the most specific stream that matches the failure:

- hook decision -> decision trace
- delivery failure -> watcher log
- operator action -> audit log
- live observer input -> monitor inbox

Do not use a later stream to explain away a missing earlier one.
