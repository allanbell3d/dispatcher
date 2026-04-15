# Dispatcher Docs Governance

## Purpose

This repo uses a deliberate split:

- `docs/` holds approved, committed operator and developer truth. **Active source of trought**
- `docs_dev/` holds draft, staging, review, planning, and execution-support material.

The goal is to keep current guidance easy to find without deleting the history and working notes that explain how the repo got here.

## Directory Contract

### `docs/`

Use `docs/` for material that is ready to be treated as the current repo truth:

- operator guides
- developer guides
- approved contracts
- approved indexes / landing pages
- approved architecture references

Files in `docs/` should be stable enough to link from onboarding, operator checklists, and future plans.

### `docs_dev/`

Use `docs_dev/` for working material:

- implementation plans
- decision notes
- backlog cleanup notes
- runbooks still being proven
- review findings
- inventories
- test evidence
- draft role packs
- frozen historical references that should not pretend to be live truth

`docs_dev/` is not a dumping ground. It is a staging area with explicit subfolders and explicit purpose.

## Promotion Rules

Promote a document from `docs_dev/` into `docs/` only when all of these are true:

1. The file matches the current repo behavior and paths.
2. The content has been de-duplicated against existing approved docs.
3. The document does not depend on unresolved placeholders, TODOs, or private side knowledge.
4. The document is useful outside the narrow session that created it.
5. The approved destination name is stable and date-free.
6. The document is linked from `docs/INDEX.md` or another approved guide.

When a draft is promoted:

- move or rewrite the content into `docs/`
- keep the original `docs_dev/` file only if it still has value as working history
- make the `docs_dev/` copy point back to the approved doc instead of acting as a second truth source

## Frozen Docs Policy

The following areas are historical references by default:

- `docs/architecture/`
- `docs_dev/specs_frozen/`
- legacy reference material under `docs_dev/ref_docs/`

Rules for frozen or historical material:

- do not rewrite historical content just to make it match live runtime behavior
- edits should be limited to indexes, link notes, or explicit annotations unless Allan approves a real spec rewrite
- when live behavior diverges, document the live contract in approved current docs instead of silently mutating history

## Naming Rules

### Approved docs in `docs/`

Use stable, date-free names in uppercase snake case:

- `INDEX.md`
- `OPERATOR_GUIDE.md`
- `DEVELOPER_GUIDE.md`
- `DOCS_GOVERNANCE.md`
- `PLAN_INGEST_CONTRACT.md`

### Working docs in `docs_dev/`

Use dated names for time-bound working material:

- plans: `YYYY-MM-DD_slug_implementation-plan.md`
- decision notes: `YYYY-MM-DD_slug_decision-note.md`
- reports / inventories: `name_YYYY-MM-DD.md` or `name_YYYY-MM-DD_suffix.md`

Use descriptive subfolders when the material is tied to a wave, review pass, or evidence set:

- `docs_dev/wave5/`
- `docs_dev/reviews/`
- `docs_dev/test_results/`
- `docs_dev/backlog/`

## Authoring Rules

- Approved docs should explain the current state, not every historical branch of the project.
- Working docs should link to approved guides for repo-wide policy rather than copying policy text inline.
- `agents/reference_prompts/` is source material and inspiration, not approved runtime truth.
- If a doc exists only to support one review or one execution pass, keep it in `docs_dev/`.

## Read Order

Start here:

1. `docs/INDEX.md`
2. `docs/OPERATOR_GUIDE.md` or `docs/DEVELOPER_GUIDE.md`
3. supporting references such as `COMMANDS.md`, `QUICKSTART.md`, `SMOKE_TEST.md`, or `docs/architecture/*`
