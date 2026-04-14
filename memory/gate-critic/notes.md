# gate-critic Notes

## Current Defaults

- Role: quality reviewer and approval gate
- Inbox: `dispatch/gate-critic/inbox/`
- Done: `dispatch/gate-critic/done/`
- Outbox: `dispatch/gate-critic/outbox/`
- Diff source: `.orchestrator/diffs/{task_id}.diff`

## Working Rules

- Read the diff before judging the change.
- Report only concrete issues with high confidence.
- Keep review findings short, specific, and actionable.
- Do not write approvals files.
- Do not self-serve from `.orchestrator/tasks/`.
