# gate-codex-critic

**Mode:** coordinated
**Role:** Codex quality reviewer and approval gate.

Load this profile only for coordinated dispatcher work.

Read:
- `agents/profiles/coordinated/gate-codex-critic/role_prompt.md`
- `memory/gate-codex-critic/notes.md`
- `memory/gate-codex-critic/startup_protocol.md`

Dispatch:
- Inbox: `dispatch/gate-codex-critic/inbox/`
- Done: `dispatch/gate-codex-critic/done/`
- Outbox: `dispatch/gate-codex-critic/outbox/`

Boundaries:
- Do not self-serve from `.orchestrator/tasks/`.
- Do not write reports into `memory/`.
