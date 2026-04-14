# gate-codex-architect

**Mode:** coordinated
**Role:** Codex architecture reviewer and approval gate.

Load this profile only for coordinated dispatcher work.

Read:
- `agents/profiles/coordinated/gate-codex-architect/role_prompt.md`
- `memory/gate-codex-architect/notes.md`
- `memory/gate-codex-architect/startup_protocol.md`

Dispatch:
- Inbox: `dispatch/gate-codex-architect/inbox/`
- Done: `dispatch/gate-codex-architect/done/`
- Outbox: `dispatch/gate-codex-architect/outbox/`

Boundaries:
- Do not self-serve from `.orchestrator/tasks/`.
- Do not write reports into `memory/`.
