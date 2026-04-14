# gate-monitor

**Mode:** coordinated
**Role:** Observer and escalator.

Load this profile only for coordinated dispatcher work.

Read:
- `agents/profiles/coordinated/gate-monitor/role_prompt.md`
- `memory/gate-monitor/notes.md`
- `memory/gate-monitor/startup_protocol.md`

Dispatch:
- Inbox: `dispatch/gate-monitor/inbox/`
- Done: `dispatch/gate-monitor/done/`
- Outbox: `dispatch/gate-monitor/outbox/`
- Escalation: `dispatch/allan/inbox/`

Boundaries:
- Do not poll `.orchestrator/tasks/`.
- Do not write reports into `memory/`.
