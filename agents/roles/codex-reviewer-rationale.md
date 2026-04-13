# Codex Reviewer Rationale

## Inputs Reused

- `agents/reference_prompts/feature-dev/code-architect.md`
  Used for stronger architecture-fit and rollout-safety thinking in `gate-codex-architect`.

- `agents/reference_prompts/feature-dev/code-reviewer.md`
  Used for higher-signal bug and regression review language in `gate-codex-critic`.

- `agents/reference_prompts/omc/critic.md`
  Used for plan-execution discipline and concrete failure-mode framing.

- `agents/reference_prompts/omc/security-auditor.md`
  Used narrowly to sharpen exploitability/security-adjacent quality checks where they materially affect correctness.

## Dispatcher-Specific Constraints

- Keep the existing watcher-compatible `review_response` JSON contract.
- Keep communication file-based under `dispatch/gate-*/...`.
- Keep startup and persistent memory under `memory/gate-*/...`.
- Do not add a new orchestration surface or custom approval format.
