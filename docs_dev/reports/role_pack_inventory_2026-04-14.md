# Dispatcher Role Pack Inventory

## Live coordinated roles

- `gate-ralph` - persistent executor for one dispatched task at a time.
- `gate-critic` - quality reviewer for correctness, regressions, and KISS.
- `gate-architect` - spec and contract reviewer for rollout safety.
- `gate-monitor` - observer and escalation gate for drift, stalls, and protocol violations.
- `gate-playwright` - batch-boundary E2E tester.

## Useful reference ingredients

- Coder/executor ingredients: `agents/reference_prompts/superpowers/verification-before-completion.md`, `agents/reference_prompts/dispatcher-plan-writer.md`.
- Critic/reviewer ingredients: `agents/reference_prompts/feature-dev/code-reviewer.md`, `agents/reference_prompts/omc/critic.md`, `agents/reference_prompts/omc/validator.md`.
- Architect ingredients: `agents/reference_prompts/feature-dev/code-architect.md`.
- Monitor ingredients: the current `gate-monitor` role prompt plus the dispatch protocol in `agents/protocols/coordinated/README.md`.
- Plan writer and auditor ingredients: `agents/reference_prompts/dispatcher-plan-writer.md`, `agents/reference_prompts/superpowers/writing-plans.md`, `agents/reference_prompts/omc/validator.md`.

## Stale patterns to remove

- Bare-name identity and old worktree path guidance.
- Direct approvals-file flow that bypasses watcher-compatible dispatch.
- Task-list polling from `.orchestrator/tasks/` in roles that should wait for dispatch.
- Terminal-peek guidance that is not part of the live coordinated protocol.

## Draft pack guidance

- Keep live role prompts short and dispatch-first.
- Keep memory notes repo-specific and current.
- Keep startup protocols to boot order, waiting behavior, and current paths.
- Keep experimental variants in `docs_dev/roles/` until Allan approves promotion.
