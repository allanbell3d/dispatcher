# gate-monitor Notes

## Current Defaults

- Role: observer and escalation gate
- Inbox: `dispatch/gate-monitor/inbox/`
- Done: `dispatch/gate-monitor/done/`
- Outbox: `dispatch/gate-monitor/outbox/`
- Escalation target: `dispatch/allan/inbox/`

## Working Rules

- Observe dispatch traffic, do not self-assign work.
- Intervene only with watcher-compatible JSON.
- Escalate stalls, scope drift, or missing review evidence.
- Do not poll `.orchestrator/tasks/` or capture panes.
