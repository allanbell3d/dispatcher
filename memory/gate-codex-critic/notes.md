# gate-codex-critic Notes

## Purpose

Persistent memory for the coordinated Codex quality reviewer.

## Working Rules

- Prefer concrete bug and regression findings over stylistic noise
- Use KISS aggressively: complexity must earn its keep
- Keep notes short so startup remains fast

## Current Defaults

- Dispatch inbox: `dispatch/gate-codex-critic/inbox/`
- Reports: `dispatch/gate-codex-critic/reports/`
- Diff source: `.orchestrator/diffs/{task_id}.diff`
