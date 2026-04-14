# Dispatcher Parallel Plan Pack

Approved docs entry points:

- `docs/INDEX.md`
- `docs/DOCS_GOVERNANCE.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/DEVELOPER_GUIDE.md`

This pack groups the next dispatcher-side workstreams that are ready for execution without more architectural conversation.

Included plans:

- `2026-04-14_docs-consolidation-governance_implementation-plan.md`
- `2026-04-14_test-template-artifact-library_implementation-plan.md`
- `2026-04-14_dispatcher-role-init-pack_implementation-plan.md`
- `2026-04-14_plan-ingest-and-backlog-normalization_implementation-plan.md`

Recommended execution order:

1. Docs consolidation governance
2. Test/template artifact library
3. Dispatcher role/init pack
4. Plan-ingest and backlog normalization

Recommended parallelization:

- Docs governance can run in parallel with the artifact library.
- Role/init pack can run in parallel with plan-ingest once the docs governance plan defines the destination document structure.
- None of these plans should block the ongoing launcher/control-plane design work.

Excluded on purpose:

- launcher/control-plane redesign
- logging/monitor realtime redesign
- hook v3.5 rewrite execution
