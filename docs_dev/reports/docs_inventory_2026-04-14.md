# Dispatcher Documentation Inventory — 2026-04-14

Snapshot taken from commit `92446a9` in the isolated plan-pack worktree.

## Summary

- The repo already has useful approved entry docs at the root: `COMMANDS.md`, `QUICKSTART.md`, and `SMOKE_TEST.md`.
- `docs/` currently acts more like an approved architecture/spec shelf than a day-to-day landing zone.
- `docs_dev/` is carrying several different jobs at once: active plans, operator runbooks, review artifacts, legacy references, and frozen history.
- The main governance gap is not a lack of documentation. It is the lack of an explicit "read here first" path and a clear promotion rule from working material into approved docs.

## Inventory By Purpose

### Approved Operator / Developer Truth

| Area | Current files | Notes |
|---|---|---|
| Session and repo status | `STATE.md`, `AGENTS.md` | Repo-level operating context and current phase notes. |
| Operator quick references | `COMMANDS.md`, `QUICKSTART.md`, `SMOKE_TEST.md` | Useful, but currently disconnected from a single approved landing page. |
| Approved architecture shelf | `docs/architecture/*.md` | Important references, but not the best first read for operators or maintainers. |

### Frozen Historical / Spec References

| Area | Current files | Notes |
|---|---|---|
| Approved historical architecture/specs | `docs/architecture/HOOK_SYSTEM_ORCHESTRATOR_GUIDE.md`, `LAUNCHER_SPEC.md`, `LIVENESS_SPEC.md`, `MASTER_*` | Keep for architecture history, constraints, and design rationale. |
| Frozen archival material | `docs_dev/specs_frozen/` | Explicitly archival. Should stay separate from live operator guidance. |
| Legacy reference material | `docs_dev/ref_docs/` | Useful provenance, but many files describe older mailbox/orchestrator flows and stale paths. |

### Active Working Plans / Runbooks

| Area | Current files | Notes |
|---|---|---|
| Implementation plans | `docs_dev/plans/*.md` | Active execution material, including this parallel plan pack. |
| Wave 5 operator runbooks | `docs_dev/wave5/*.md` | Real operator support material, but still working-stage and scenario-specific. |
| Backlog / alignment notes | `docs_dev/backlog/`, `docs_dev/reviewer_activation.md`, `docs_dev/master_spec_alignment_approval_2026-04-14.md`, `docs_dev/CURRENT_CONTRACT.md` | Important staging material that should point at approved docs instead of becoming alternate truth. |

### Reviews / Findings / Evidence

| Area | Current files | Notes |
|---|---|---|
| Reports | `docs_dev/reports/` | Good home for inventories, audits, and one-off analysis outputs. |
| Reviews | `docs_dev/reviews/` | Review prompts and historical outputs. |
| Test evidence | `docs_dev/test_results/` | Verification notes and evidence, not operator entry docs. |

### Stale / Duplicate Truth Candidates

| Topic | Current overlap | Drift / risk |
|---|---|---|
| Quick start | `QUICKSTART.md` vs `docs_dev/ref_docs/QUICKSTART.md` | Root file reflects current dispatcher flow; `ref_docs` copy reflects older gate/mailbox/orchestration paths. |
| Smoke flow | `SMOKE_TEST.md` vs `docs_dev/ref_docs/SMOKE_TEST.md` | Root file documents current dispatcher checks; `ref_docs` version is historical and references older gate paths and lifecycle steps. |
| Operator flow | Root docs vs `docs_dev/wave5/*.md` | Wave 5 docs are useful scenario runbooks, but they overlap with launcher/watcher/startup guidance that should have one approved operator guide. |
| Live contract vs frozen specs | `docs_dev/CURRENT_CONTRACT.md` / `master_spec_alignment_approval_2026-04-14.md` vs `docs/architecture/MASTER_SPECS_MERGED.md` | Live repo reality and frozen spec history are mixed without a clear "current truth vs historical reference" entry path. |
| Plan contract guidance | `docs_dev/plans/WATCHER_PLAN_FORMAT_GUIDE.md` vs `agents/reference_prompts/dispatcher-plan-writer.md` | Same contract is expressed in two places, with no approved contract doc yet. |

## Recommended Promotion Targets

- Add `docs/INDEX.md` as the approved landing page.
- Add `docs/OPERATOR_GUIDE.md` for the main operator path.
- Add `docs/DEVELOPER_GUIDE.md` for repo/runtime orientation.
- Add `docs/DOCS_GOVERNANCE.md` to make the `docs/` vs `docs_dev/` split explicit.

## Recommended Guardrails

- Keep `docs/architecture/` and `docs_dev/specs_frozen/` as historical references, not operator onboarding.
- Keep plans, reviews, cleanup notes, and scenario runbooks in `docs_dev/`.
- Make working docs link to approved guides for policy instead of restating repo-wide rules.
