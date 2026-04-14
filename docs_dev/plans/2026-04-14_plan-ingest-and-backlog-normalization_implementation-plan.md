# Dispatcher Plan Ingest And Backlog Normalization Implementation Plan

Approved docs entry points:

- `docs/INDEX.md`
- `docs/DOCS_GOVERNANCE.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/DEVELOPER_GUIDE.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize watcher-ingestible plans and clean/enrich the first real backlog so the dispatcher can consume real sprint work consistently without formatting drift.

**Architecture:** Treat plan format and backlog hygiene as one ingestion track: define one canonical plan contract, provide a generator/normalizer path, and clean the backlog to match the same truth.

**Tech Stack:** JSON tasks, Markdown plans, watcher plan format guidance, normalization tooling.

---

### Task 1: Freeze The Canonical Plan Contract

**Files:**
- Read: `docs_dev/plans/WATCHER_PLAN_FORMAT_GUIDE.md`
- Read: `.orchestrator/tasks/tasks.json`
- Create: `docs/PLAN_INGEST_CONTRACT.md`

- [ ] **Step 1: Write one approved ingest contract**
Document:
  - required plan structure
  - required metadata
  - acceptable headings/sections
  - what watcher/normalizer expects

- [ ] **Step 2: Commit**

```bash
git add docs/PLAN_INGEST_CONTRACT.md
git commit -m "docs: add dispatcher plan ingest contract"
```

### Task 2: Build Or Tighten Plan Normalization Tooling

**Files:**
- Modify or create: `scripts/normalize_plan.py`
- Add tests: `tests/test_plan_normalization.py`

- [ ] **Step 1: Write failing normalization tests**
Cover:
  - valid watcher plan passes
  - malformed headings normalize or fail clearly
  - output is stable and deterministic

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_plan_normalization.py -q
```

- [ ] **Step 3: Implement or tighten normalizer**
Make the tool produce watcher-safe output from draft plans.

- [ ] **Step 4: Run tests to verify pass**

```bash
python -m pytest tests/test_plan_normalization.py -q
```

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize_plan.py tests/test_plan_normalization.py
git commit -m "feat: tighten dispatcher plan normalization"
```

### Task 3: Backlog Cleanup And Enrichment

**Files:**
- Modify: `.orchestrator/tasks/tasks.json`
- Create: `docs_dev/backlog/tasks_cleanup_notes_2026-04-14.md`

- [ ] **Step 1: Audit current task formatting**
Identify:
  - duplicate acceptance criteria
  - malformed text
  - inconsistent IDs
  - missing useful detail for first real orchestrator sprint

- [ ] **Step 2: Clean and enrich the backlog**
Keep formatting consistent and make the first 50-bug plan feedable to the engine.

- [ ] **Step 3: Commit**

```bash
git add .orchestrator/tasks/tasks.json docs_dev/backlog/tasks_cleanup_notes_2026-04-14.md
git commit -m "docs: normalize and enrich dispatcher backlog"
```

### Task 4: Add Agent-Facing Plan Writer Guidance

**Files:**
- Modify or create: `agents/reference_prompts/dispatcher-plan-writer.md`
- Cross-link: `docs/PLAN_INGEST_CONTRACT.md`

- [ ] **Step 1: Align the plan-writer prompt to the ingest contract**
Make sure generated plans match the approved watcher-ingest format.

- [ ] **Step 2: Add examples or checklist**
Give the plan writer enough concrete guidance to stop format drift.

- [ ] **Step 3: Commit**

```bash
git add agents/reference_prompts/dispatcher-plan-writer.md docs/PLAN_INGEST_CONTRACT.md
git commit -m "docs: align dispatcher plan writer to ingest contract"
```

### Test Plan

- Validate generated/normalized plans against the ingest contract.
- Verify backlog formatting is consistent and readable.
- Confirm watcher-oriented plan output is stable enough for real sprint use.

### Assumptions

- The first real orchestrator sprint will use the cleaned backlog and normalized plan format.
- Plan normalization is more important than fancy plan-generation UX in this phase.
