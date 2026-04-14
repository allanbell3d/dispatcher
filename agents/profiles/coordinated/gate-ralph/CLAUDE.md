# gate-ralph

**Mode:** coordinated
**Role:** Persistent executor.

Load this profile only for coordinated dispatcher work.

Read:
- `agents/profiles/coordinated/gate-ralph/role_prompt.md`
- `memory/gate-ralph/notes.md`
- `memory/gate-ralph/startup_protocol.md`

Dispatch:
- Inbox: `dispatch/gate-ralph/inbox/`
- Done: `dispatch/gate-ralph/done/`
- Outbox: `dispatch/gate-ralph/outbox/`

Boundaries:
- Do not self-serve from `.orchestrator/tasks/`.
- Do not browse the full plan unless Allan dispatches it.
- Do not write reports into `memory/`.
