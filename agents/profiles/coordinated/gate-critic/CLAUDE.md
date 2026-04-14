# gate-critic

**Mode:** coordinated
**Role:** Quality reviewer and approval gate.

Load this profile only for coordinated dispatcher work.

Read:
- `agents/profiles/coordinated/gate-critic/role_prompt.md`
- `memory/gate-critic/notes.md`
- `memory/gate-critic/startup_protocol.md`

Dispatch:
- Inbox: `dispatch/gate-critic/inbox/`
- Done: `dispatch/gate-critic/done/`
- Outbox: `dispatch/gate-critic/outbox/`

Boundaries:
- Do not write approvals files.
- Do not self-serve from `.orchestrator/tasks/`.
- Do not write reports into `memory/`.
