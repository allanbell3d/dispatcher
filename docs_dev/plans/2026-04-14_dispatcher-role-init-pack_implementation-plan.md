# Dispatcher Role Init Pack Implementation Plan

Approved docs entry points:

- `docs/INDEX.md`
- `docs/DOCS_GOVERNANCE.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/DEVELOPER_GUIDE.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Massively improve dispatcher agent role files, memory/init notes, and coordinated startup guidance using the existing `agents/reference_prompts` library as source material.

**Architecture:** Keep one live coordinated profile set, but rebuild the role and init content around clearer responsibilities, stronger startup discipline, and better dispatch/review workflow instructions. Use reference prompts as ingredients, not as raw copies.

**Tech Stack:** Markdown role files, memory files, startup docs, prompt library.

---

### Task 1: Inventory Live Roles And References

**Files:**
- Read: `agents/profiles/coordinated/`
- Read: `agents/protocols/coordinated/README.md`
- Read: `memory/`
- Read: `agents/reference_prompts/`
- Create: `docs_dev/reports/role_pack_inventory_2026-04-14.md`

- [ ] **Step 1: Map live profiles to responsibilities**
List current coordinated agents and their intended role in the workflow.

- [ ] **Step 2: Map useful reference prompt ingredients**
Identify which reference prompts are useful for:
  - coder
  - critic/reviewer
  - architect
  - monitor
  - plan writer / auditor

- [ ] **Step 3: Commit**

```bash
git add docs_dev/reports/role_pack_inventory_2026-04-14.md
git commit -m "docs: add dispatcher role pack inventory"
```

### Task 2: Define The New Role Pack Contract

**Files:**
- Create: `docs_dev/roles/ROLE_PACK_CONTRACT.md`

- [ ] **Step 1: Write the role-pack contract**
Define:
  - one runtime role file per agent
  - one memory `notes.md`
  - one startup protocol
  - one optional `startup/` folder
  - what belongs in role file vs memory vs startup docs

- [ ] **Step 2: Commit**

```bash
git add docs_dev/roles/ROLE_PACK_CONTRACT.md
git commit -m "docs: define dispatcher role pack contract"
```

### Task 3: Rebuild Core Coordinated Profiles

**Files:**
- Modify: `agents/profiles/coordinated/*`
- Modify: `agents/protocols/coordinated/README.md`

- [ ] **Step 1: Rewrite the core profiles**
At minimum cover:
  - coder
  - critic
  - architect
  - monitor

Focus on:
  - actual dispatcher workflow
  - no stale path guidance
  - no fake approvals-file flow
  - better startup behavior and reporting

- [ ] **Step 2: Update the coordinated protocol readme**
Make it match the rewritten roles and startup expectations.

- [ ] **Step 3: Commit**

```bash
git add agents/profiles/coordinated agents/protocols/coordinated/README.md
git commit -m "docs: rebuild dispatcher coordinated role pack"
```

### Task 4: Rebuild Memory And Init Notes

**Files:**
- Modify: `memory/*/notes.md`
- Create or modify: `memory/*/startup/`

- [ ] **Step 1: Normalize memory notes**
Make each memory notes file:
  - repo-specific
  - role-specific
  - concise
  - not copied from another project

- [ ] **Step 2: Seed startup docs where needed**
Use startup docs only for real required context, not filler.

- [ ] **Step 3: Commit**

```bash
git add memory
git commit -m "docs: normalize dispatcher memory and startup notes"
```

### Task 5: Create Experimental Drafts Outside Live Profiles

**Files:**
- Create: `docs_dev/roles/`

- [ ] **Step 1: Draft stronger coder/auditor variants in `docs_dev/roles`**
Use the reference prompt library to draft better role content without making it live by default.

- [ ] **Step 2: Document promotion criteria**
Describe when a draft role is ready to replace a live profile.

- [ ] **Step 3: Commit**

```bash
git add docs_dev/roles
git commit -m "docs: add dispatcher role draft pack"
```

### Test Plan

- Confirm every live coordinated agent has:
  - a clear role file
  - a repo-specific memory notes file
  - startup guidance that matches current dispatcher flow
- Confirm no live role file still references stale bare-name or approvals-file behavior.

### Assumptions

- Reference prompts are ingredients, not source-of-truth runtime prompts.
- Experimental variants live in `docs_dev/roles` until approved.
