# Dispatcher Role Pack Contract

## Purpose

This contract defines how the coordinated dispatcher role pack is split between live runtime files and draft material.

## Live runtime files

Each coordinated agent gets one runtime role file, one notes file, and one startup protocol:

- Runtime role file: `agents/profiles/coordinated/gate-<name>/role_prompt.md`
- Memory notes: `memory/gate-<name>/notes.md`
- Startup protocol: `memory/gate-<name>/startup_protocol.md`
- Optional startup folder: `memory/gate-<name>/startup/`

## What belongs where

### Role file

- Stable identity
- Core responsibilities
- Dispatch workflow
- Boundaries and stop conditions
- Output format expectations

### Memory notes

- Repo-specific defaults
- Current inbox/outbox paths
- Short-lived caveats and reminders
- A few active lessons, not history dumps

### Startup protocol

- Read order
- Waiting behavior
- What to do when dispatch arrives
- What to do when the input is incomplete

### Optional startup folder

- Use only when a role needs more than one small startup document.
- Keep it focused on boot-time context, not long-form history.

## Live rules

- No bare-name identities in live files.
- No old worktree or legacy path guidance.
- No task self-service from `.orchestrator/tasks/` unless a role explicitly requires a task file as dispatched input.
- No approvals-file flow that bypasses watcher-compatible dispatch.
- No reports written into `memory/`.
- Keep `docs_dev/` as draft or staging material, not live runtime truth.

## Promotion criteria for drafts

A draft role is ready to promote when:

- It matches the live dispatch paths and current role contract.
- It removes stale path, identity, and approvals-flow guidance.
- It is concise enough for startup use.
- It was checked against the current role prompt and a sample dispatch path.
- Allan has approved it for promotion into the live profile set.

## Draft policy

- Experimental role variants stay in `docs_dev/roles/` until promoted.
- Live runtime files should not depend on draft-only content.
- Drafts may be stronger or more opinionated, but they must stay repo-specific and KISS.
