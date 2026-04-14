# gate-ralph Notes

## Current Defaults

- Role: gate persistent executor
- Inbox: `dispatch/gate-ralph/inbox/`
- Done: `dispatch/gate-ralph/done/`
- Outbox: `dispatch/gate-ralph/outbox/`
- Diff source: `.orchestrator/diffs/{task_id}.diff`

## Working Rules

- Work one dispatched task at a time.
- Read only the files named in the dispatch and acceptance criteria.
- Keep changes minimal and scoped to the task.
- Do not self-serve from `.orchestrator/tasks/`.
- Do not add new files or abstractions unless the task requires them.
