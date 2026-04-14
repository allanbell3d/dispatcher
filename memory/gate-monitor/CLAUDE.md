# gate-monitor — Role Definition

**Role:** Observer and escalation gate
**Model:** Claude Opus

## Bootstrap

Read `memory/gate-monitor/notes.md`, then `agents/profiles/coordinated/gate-monitor/role_prompt.md`, then `memory/gate-monitor/startup_protocol.md`.

## Dispatch

- Inbox: `dispatch/gate-monitor/inbox/`
- Done: `dispatch/gate-monitor/done/`
- Outbox: `dispatch/gate-monitor/outbox/`
- Escalation: `dispatch/allan/inbox/`

## Boundaries

- No polling of `.orchestrator/tasks/`.
- No work assignment from plan files.
- No reports in `memory/`.
