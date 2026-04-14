# Dispatcher Developer Guide

## Purpose

This guide is for maintainers working on the dispatcher repo itself: hooks, watcher behavior, launcher flow, profiles, docs, and contracts.

## Repo Layout

| Path | Purpose |
|---|---|
| `.orchestrator/` | Canonical sample/runtime state tree used by the repo and by tests. |
| `agents/profiles/coordinated/` | Live coordinated role files used by dispatcher agents. |
| `agents/reference_prompts/` | Source material and prompt ingredients. Useful reference, not runtime truth. |
| `artifacts/` | Canonical seed, fixture, and example library for bootstrap, tests, and docs. |
| `bin/` | Launcher entry points. `orch_launcher.ps1` is primary. |
| `docs/` | Approved guides, contracts, indexes, and architecture references. |
| `docs_dev/` | Drafts, plans, reports, reviews, working runbooks, and frozen reference material. |
| `hooks/` | Hook entry points installed into Claude project settings. |
| `lib/` | Shared Python helpers such as path resolution and atomic writes. |
| `memory/` | Repo-specific memory overlays and startup notes for gate agents. |
| `schemas/` | Config schema and related validation sources. |
| `scripts/` | CLI entry points and support tooling such as validation, hook install, watcher control, and normalization helpers. |
| `tests/` | Pytest coverage for hooks, watcher behavior, CLI surfaces, and contracts. |

## Runtime Contracts

Current runtime behavior depends on a few repo-wide contracts:

- agent identity is `gate-*` everywhere
- runtime paths resolve from `.orchestrator/config.json` first and `lib.common.resolve_path()` defaults second
- live traffic goes through `dispatch/<agent>/...`
- `.orchestrator/` is runtime state, not an agent mailbox
- `task_id` is the canonical task identity
- merged verdicts are stored at `.orchestrator/merged_verdicts/<task_id>.json`

When behavior changes, update the approved docs and tests together.

## Important Runtime Paths

| Contract | Canonical path |
|---|---|
| Config | `.orchestrator/config.json` |
| Plans | `.orchestrator/plans/` |
| Backlog tasks | `.orchestrator/tasks/tasks.json` |
| Current task | `.orchestrator/tasks/current_task.json` |
| Dispatch root | `dispatch/` |
| Trackers | `.orchestrator/trackers.json` |
| Audit log | `.orchestrator/audit.log` |
| Decision trace | `.orchestrator/logs/decision_trace.log` |
| Merged verdicts | `.orchestrator/merged_verdicts/` |
| Runtime halt flags | `.orchestrator/halts/` |

## Tests

Primary automated verification lives under `tests/` and is organized around contracts:

- CLI behavior
- hook enforcement and observability
- watcher routing and fan-in
- launcher behavior
- task and role config
- plan generation / normalization

If a change affects a contract, add or update a test close to the affected area instead of relying on a broad manual claim.

## Docs Promotion

Dispatcher documentation is intentionally split:

- `docs/` is approved truth
- `docs_dev/` is staging and working material

Promotion rules live in [`DOCS_GOVERNANCE.md`](DOCS_GOVERNANCE.md). New approved guides and contracts should be stable, date-free, and linked from [`INDEX.md`](INDEX.md).

## Historical And Frozen References

Not every useful file is current truth.

- `docs/architecture/` holds approved architecture/spec references and historical design material.
- `docs_dev/specs_frozen/` holds frozen archival artifacts.
- `docs_dev/ref_docs/` holds older reference material that remains useful for provenance and comparison.

When the repo diverges from historical references, document live behavior in approved current docs rather than silently rewriting the past.

## Maintainer Rules Of Thumb

- Preserve the `docs/` vs `docs_dev/` split.
- Use `agents/reference_prompts/` as source material, not as raw runtime truth.
- Keep changes KISS and evidence-based.
- Prefer updating docs, tests, and contracts together when changing a live behavior.
