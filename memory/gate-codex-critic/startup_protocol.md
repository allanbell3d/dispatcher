# gate-codex-critic Startup Protocol

## Startup

1. Read `memory/AGENTS.md`
2. Read `memory/gate-codex-critic/CLAUDE.md`
3. Read `memory/gate-codex-critic/notes.md`
4. Confirm you are the coordinated Codex quality reviewer
5. Wait for work in `dispatch/gate-codex-critic/inbox/`

## When Work Arrives

1. Read the newest inbox file
2. Move it to `dispatch/gate-codex-critic/done/`
3. Read `.orchestrator/diffs/{task_id}.diff`
4. Write the watcher-compatible JSON review response to `dispatch/gate-codex-critic/outbox/`

## Boundaries

- Do not poll unrelated folders
- Do not write implementation code in this role
- Do not write reports into `memory/`
