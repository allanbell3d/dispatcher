# Codex Reviewer Rationale

This note records why the new coordinated Codex reviewer overlays exist.

## Purpose

- Keep the Codex reviewer roles aligned with the existing gate-architect and gate-critic contracts.
- Use the live `memory/` and `dispatch/gate-codex-*` layout instead of introducing new runtime code or config.
- Reuse the review tone, JSON response shape, and inbox-to-outbox flow already established for the gate reviewers.

## Source Patterns Reused

- `agents/profiles/coordinated/gate-architect/CLAUDE.md`
- `agents/profiles/coordinated/gate-architect/role_prompt.md`
- `agents/profiles/coordinated/gate-critic/CLAUDE.md`
- `agents/profiles/coordinated/gate-critic/role_prompt.md`
- `agents/reference_prompts/feature-dev/code-reviewer.md`
- `agents/reference_prompts/omc/code-reviewer.md`
- `agents/reference_prompts/omc/critic.md`

## Contract

- Read-only review roles.
- No runtime code changes.
- No config changes.
- Responses stay in the existing JSON review format.
- Paths should remain scoped to `dispatch/gate-codex-architect/` and `dispatch/gate-codex-critic/` for the new overlays.
