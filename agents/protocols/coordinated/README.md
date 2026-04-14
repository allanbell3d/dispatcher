# Coordinated agent protocol

These profiles are for the `gate-*` agents only.

Load order:

1. shared coordinated profile
2. shared coordinated role prompt
3. project-local `memory/gate-<name>/notes.md`
4. project-local `memory/gate-<name>/startup_protocol.md`
5. current dispatch item in `dispatch/gate-<name>/inbox/`

Rules:

- Do not browse the full plan unless Allan explicitly dispatches it.
- Do not self-serve work from `.orchestrator/tasks/` or `tasks.json`.
- Do not read another agent's memory folder by default.
- Do not treat `.orchestrator/` as a mailbox.
- Live traffic goes through `dispatch/gate-<name>/inbox/`, `done/`, and `outbox/`.
- Reviewers read `.orchestrator/diffs/{task_id}.diff` and respond with watcher-compatible JSON.
- `gate-monitor` observes dispatch traffic and escalates drift or stalls to Allan.
