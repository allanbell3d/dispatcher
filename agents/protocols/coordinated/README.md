# Coordinated agent protocol

These profiles are for the `gate-*` agents only.

Load order:

1. shared coordinated profile
2. shared coordinated role prompt
3. project-local `memory/gate-<name>/...`
4. current file from `dispatch/gate-<name>/inbox/`

Rules:

- do not browse the full plan unless Allan explicitly dispatches it
- do not self-serve tasks from `.orchestrator/tasks/`
- do not read another agent's memory folder by default
- do not treat `.orchestrator/` as a mailbox
- all live traffic goes through `dispatch/gate-<name>/...`
- reviewer routing comes from `.orchestrator/config.json -> reviewers.active`
- active reviewer presets may include classic, codex, hybrid, or all-four combinations
