# Dispatcher Artifact Library

This folder is the canonical home for reusable dispatcher templates, fixtures, and examples.

## Layout

| Path | Purpose |
|---|---|
| `install/` | Copyable bootstrap seeds for fresh project setup. |
| `fixtures/` | Machine-oriented test inputs and sample payloads. |
| `examples/` | Human-readable examples for operators and maintainers. |

## Rules

- `install/` is for seed material that a bootstrap flow can copy or adapt.
- `fixtures/` is for tests and scripts. Prefer these over ad hoc inline scaffolds.
- `examples/` is for readable samples that show the current contract shape without pretending to be runtime state.
- Runtime state remains in `.orchestrator/` and `dispatch/`; this folder is the reusable source library, not the live engine state.

## Naming

- `*.seed.json` = bootstrapable seed
- `*.template.json` or `*.template.md` = sample input meant to be edited or rendered
- `*.example.json` or `*.example.md` = operator-facing example
- `*.valid.json` / `*.malformed.*.json` = test fixture

## Copy vs Example

- Copy from `install/` when creating or seeding a project.
- Load from `fixtures/` in tests and smoke helpers.
- Link to `examples/` from docs when showing operators what valid artifacts look like.
