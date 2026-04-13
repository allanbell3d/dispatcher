# Project-local orchestration control plane

This folder is intentionally project-local.

It contains:

- `config.json`
- `tasks/`
- `plans/`
- `diffs/`
- `logs/`
- `runtime_flags/`
- `merged_verdicts/`
- `halts/`
- `bin/`

The engine code itself lives outside the repo in the shared orchestrator root.

Current live contract notes:

- Agent identity is `gate-*` everywhere.
- Current task lives at `.orchestrator/tasks/current_task.json`.
- Decision trace lives under `.orchestrator/logs/`.
- Merged verdicts are the review gate input; legacy approvals files are no longer authoritative.
