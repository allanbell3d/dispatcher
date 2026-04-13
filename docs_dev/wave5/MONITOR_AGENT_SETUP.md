# Monitor Agent Setup

## Inputs

- watcher CC traffic
- `monitor_ingest.py` JSON activity messages in `dispatch/gate-monitor/inbox/`
- optional fallback activity mail delivered by `watcher.py` when `session.monitor_activity_to_dispatch=true`

## Expected Location

- inbox: `dispatch/gate-monitor/inbox/`
- notes: `memory/gate-monitor/notes.md`

## Healthy Signal

- new `.json` activity files appear during coder tool use
- watcher pulse / escalation messages appear during sprint traffic
- if fallback is enabled, `.md` activity mail also appears after watcher delivery

## Notes

- Primary monitor stream is `monitor_ingest.py`.
- Fallback stream is slower and watcher-mediated; use it only when explicitly enabled for comparison or backup.
