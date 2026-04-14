# Monitor Agent Setup

## Inputs

- watcher CC traffic
- `monitor_ingest.py` rendered monitor payloads in `dispatch/gate-monitor/inbox/`
- reviewer session output when Ralph is idle or a reviewer emits meaningful decision/warning signal
- optional legacy fallback activity mail delivered by `watcher.py` when `session.monitor_activity_to_dispatch=true`

## Expected Location

- inbox: `dispatch/gate-monitor/inbox/`
- notes: `memory/gate-monitor/notes.md`
- durable trace: `.orchestrator/logs/monitor_trace.jsonl`

## Healthy Signal

- new `.json` monitor payloads appear during coder tool use
- payloads include rendered monitor text, not only tool summaries
- durable trace rows append to `.orchestrator/logs/monitor_trace.jsonl`
- watcher pulse / escalation messages appear during sprint traffic
- if fallback is enabled manually, `.md` activity mail also appears after watcher delivery

## Notes

- Primary monitor stream is `monitor_ingest.py`, but it now tails Claude session JSONL and renders monitor-safe text from parsed session events.
- The hook payload is only the trigger/session locator. The transcript is the source of truth.
- One monitor target is used today, but routing is already fan-out capable.
- Fallback stream is legacy, slower, and watcher-mediated; use it only when explicitly enabled for comparison or backup.
