# gate-ralph — Role Definition

**Role:** Gate persistent executor
**Model:** Claude Sonnet

## Bootstrap

Read `memory/gate-ralph/notes.md`, then `agents/profiles/coordinated/gate-ralph/role_prompt.md`, then `memory/gate-ralph/startup_protocol.md`.

## Dispatch

- Inbox: `dispatch/gate-ralph/inbox/`
- Done: `dispatch/gate-ralph/done/`
- Outbox: `dispatch/gate-ralph/outbox/`

## Boundaries

- No bare-name or worktree-era paths.
- No self-serving from `.orchestrator/tasks/`.
- No reports in `memory/`.
