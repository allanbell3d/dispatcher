# Dispatcher Test Template Artifact Library Implementation Plan

Approved docs entry points:

- `docs/INDEX.md`
- `docs/DOCS_GOVERNANCE.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/DEVELOPER_GUIDE.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable library of test and template artifacts that can be used both for dispatcher install/bootstrap and for local dev/testing without duplicating ad hoc fixture files across the repo.

**Architecture:** Create one canonical artifact library with clear categories: install/bootstrap artifacts, sprint/test fixtures, and operator examples. Consumers should copy or render from this library instead of inventing their own fixtures each time.

**Tech Stack:** Markdown, JSON, fixture files, dispatcher config/task/plan examples, tests.

---

### Task 1: Define Artifact Library Structure

**Files:**
- Create: `artifacts/README.md`
- Create: `artifacts/install/`
- Create: `artifacts/fixtures/`
- Create: `artifacts/examples/`

- [ ] **Step 1: Create top-level structure**
Use:
  - `artifacts/install/` for bootstrapable package assets
  - `artifacts/fixtures/` for test fixtures
  - `artifacts/examples/` for operator-facing sample artifacts

- [ ] **Step 2: Document what belongs where**
Write `artifacts/README.md` with category rules and naming conventions.

- [ ] **Step 3: Commit**

```bash
git add artifacts
git commit -m "chore: scaffold dispatcher artifact library"
```

### Task 2: Seed Install Artifacts

**Files:**
- Create: `artifacts/install/config/`
- Create: `artifacts/install/tasks/`
- Create: `artifacts/install/plans/`

- [ ] **Step 1: Add install-ready seed artifacts**
Include minimal:
  - config template
  - idle project task directory template
  - current-task placeholder example
  - launcher/watcher seed support files if needed

- [ ] **Step 2: Document intended install use**
Explain which artifacts are copied during project bootstrap and which are only examples.

- [ ] **Step 3: Commit**

```bash
git add artifacts/install
git commit -m "feat: add dispatcher install artifact seeds"
```

### Task 3: Seed Test Fixtures

**Files:**
- Create: `artifacts/fixtures/tasks/`
- Create: `artifacts/fixtures/plans/`
- Create: `artifacts/fixtures/dispatch/`
- Modify: `tests/` references as needed

- [ ] **Step 1: Add reusable fixtures**
Include:
  - idle project
  - sprint-ready project
  - malformed plan/task samples
  - dispatch inbox/outbox samples
  - monitor message samples

- [ ] **Step 2: Update tests to prefer canonical fixtures**
Reduce one-off embedded fixture sprawl where practical.

- [ ] **Step 3: Commit**

```bash
git add artifacts/fixtures tests
git commit -m "test: add reusable dispatcher fixture library"
```

### Task 4: Add Operator Examples

**Files:**
- Create: `artifacts/examples/tasks/`
- Create: `artifacts/examples/plans/`
- Create: `artifacts/examples/messages/`

- [ ] **Step 1: Add readable operator examples**
Include:
  - valid task list example
  - valid current task example
  - valid watcher-ingestible plan example
  - valid review request / monitor message example

- [ ] **Step 2: Cross-link examples from docs**
Point operator/developer docs to the example library.

- [ ] **Step 3: Commit**

```bash
git add artifacts/examples docs
git commit -m "docs: add dispatcher artifact examples"
```

### Test Plan

- Verify install/bootstrap code can read from `artifacts/install`.
- Verify tests can consume `artifacts/fixtures`.
- Verify example files are human-readable and match the current contract.

### Assumptions

- The artifact library is repo truth for fixtures/templates, not a dumping ground.
- Existing ad hoc samples can be migrated gradually.
