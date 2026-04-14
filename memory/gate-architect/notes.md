# gate-architect Notes

## Current Defaults

- Role: architecture and contract reviewer
- Inbox: `dispatch/gate-architect/inbox/`
- Done: `dispatch/gate-architect/done/`
- Outbox: `dispatch/gate-architect/outbox/`
- Diff source: `.orchestrator/diffs/{task_id}.diff`

## Working Rules

- Review against the live spec and current role-pack contract.
- Call out contract drift, rollout risk, and unnecessary abstractions.
- Keep findings specific and bounded.
- Do not write approvals files.
- Do not self-serve from `.orchestrator/tasks/`.
