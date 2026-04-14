# Dispatcher Docs Consolidation Governance Implementation Plan

Approved docs entry points:

- `docs/INDEX.md`
- `docs/DOCS_GOVERNANCE.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/DEVELOPER_GUIDE.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate dispatcher documentation into an understandable approved-doc system where `docs/` is committed truth and `docs_dev/` is the staging area for draft, review, and execution material.

**Architecture:** Preserve the current split between approved and working docs, but add explicit governance, consolidated guides, and promotion rules. Reduce duplicate truth sources and make it obvious where operators should read first.

**Tech Stack:** Markdown, repo docs, launcher/operator references, frozen architecture docs.

---

### Task 1: Inventory Current Documentation

**Files:**
- Read: `docs/`
- Read: `docs_dev/`
- Create: `docs_dev/reports/docs_inventory_2026-04-14.md`

- [ ] **Step 1: Inventory docs by purpose**
Group docs into:
  - approved operator truth
  - frozen historical/spec references
  - active working plans
  - reviews/findings
  - stale/duplicate candidates

- [ ] **Step 2: Identify duplicate truth**
List cases where the same topic exists in both `docs/` and `docs_dev/` with drift.

- [ ] **Step 3: Commit**

```bash
git add docs_dev/reports/docs_inventory_2026-04-14.md
git commit -m "docs: add dispatcher documentation inventory"
```

### Task 2: Define Docs Governance Rules

**Files:**
- Create: `docs/DOCS_GOVERNANCE.md`
- Modify: `STATE.md`

- [ ] **Step 1: Write docs governance**
Define:
  - `docs/` = approved, committed operator/developer truth
  - `docs_dev/` = draft, review, staging, and execution support
  - promotion criteria from `docs_dev` to `docs`
  - frozen docs policy
  - naming rules for new plans/specs/guides

- [ ] **Step 2: Add a short reference in `STATE.md`**
Point future contributors to the governance doc.

- [ ] **Step 3: Commit**

```bash
git add docs/DOCS_GOVERNANCE.md STATE.md
git commit -m "docs: add dispatcher docs governance"
```

### Task 3: Create Consolidated Operator Guide

**Files:**
- Create: `docs/OPERATOR_GUIDE.md`
- Read: `COMMANDS.md`
- Read: `QUICKSTART.md`
- Read: `SMOKE_TEST.md`
- Read: `docs_dev/wave5/*.md`

- [ ] **Step 1: Write a single operator guide**
Cover:
  - what the dispatcher is
  - install health vs sprint readiness
  - launcher entry points
  - watcher basics
  - task basics
  - where logs live
  - where reviews/plans live

- [ ] **Step 2: De-duplicate surrounding docs**
Keep smaller docs as supporting references, not competing entry points.

- [ ] **Step 3: Commit**

```bash
git add docs/OPERATOR_GUIDE.md
git commit -m "docs: add consolidated dispatcher operator guide"
```

### Task 4: Create Consolidated Developer Guide

**Files:**
- Create: `docs/DEVELOPER_GUIDE.md`
- Read: `docs/architecture/*.md`
- Read: `docs_dev/ref_docs/*`

- [ ] **Step 1: Write a developer guide**
Cover:
  - repo structure
  - runtime contracts
  - config/state/tasks/plans paths
  - where tests live
  - how docs promotion works
  - where legacy/frozen references are kept

- [ ] **Step 2: Commit**

```bash
git add docs/DEVELOPER_GUIDE.md
git commit -m "docs: add consolidated dispatcher developer guide"
```

### Task 5: Promotion And Cleanup Pass

**Files:**
- Modify: `docs_dev/plans/*` as needed for cross-links
- Modify: `docs/architecture/*` only for links/indexes, not frozen content
- Create: `docs/INDEX.md`

- [ ] **Step 1: Create docs index**
Create one landing index in `docs/INDEX.md` pointing to:
  - operator guide
  - developer guide
  - architecture docs
  - frozen specs

- [ ] **Step 2: Cross-link staged docs cleanly**
Make sure draft plans in `docs_dev` reference the approved guides instead of restating policy.

- [ ] **Step 3: Commit**

```bash
git add docs/INDEX.md docs_dev/plans
git commit -m "docs: add consolidated docs index and cross-links"
```

### Test Plan

- Read `docs/INDEX.md` and confirm it gives a usable entry path in under 2 minutes.
- Verify no frozen spec content is rewritten unless explicitly approved.
- Verify `docs/` and `docs_dev/` purposes are explicit and non-overlapping.

### Assumptions

- `docs_dev/` remains the working/staging area by design.
- Frozen specs remain historical references unless separately approved for edits.
