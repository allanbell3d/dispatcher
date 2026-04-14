# Dispatcher Backlog Cleanup Notes

## Scope

Cleanup and normalize `.orchestrator/tasks/tasks.json` for the first live orchestrator sprint.

## Applied Normalization

- kept the existing task IDs and batch ordering stable
- removed prose-only duplication from the B33/B39 and B32/B49 pairs
- added structured `deps` hints where the follow-on task depends on the lead task
- kept the backlog schema backward-compatible by only adding optional metadata

## Notes

- `B33` remains the primary edit-clarification task and `B39` now references it structurally
- `B32` remains the primary all-rooms context task and `B49` now references it structurally
- no task IDs were merged or deleted in this pass
