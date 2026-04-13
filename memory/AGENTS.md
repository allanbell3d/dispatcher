# Agent System — Identity, Permissions & Orchestration

This file is read first by every agent session. It explains how the multi-agent system works, what you can and cannot do, and where your files live.

Your role definition is in `memory/<your-folder>/CLAUDE.md`. Read it after this file.

---

## Memory Folder Structure

```
memory/
├── CLAUDE.md                     ← YOU ARE HERE
├── session-continuation.md       ← Project handoff state (Orchestrator only)
├── <agent>/
│   ├── CLAUDE.md                 ← Your frozen role definition (do not edit)
│   ├── notes.md                  ← Your session memory (you write this)
│   ├── feedback_*.md             ← Corrections from Allan (read-only)
│   ├── to-inject/                ← Hook-injected at session start
│   ├── snapshots/                ← State snapshots at compact/stop
│   ├── transcriptions/           ← Session transcripts (auto-generated)
│   └── archive/                  ← Old notes versions
```

Not all agents have all subfolders — only agents requiring injection get them.

---

## Agent Roster

| Agent | Folder | Role |
|-------|--------|------|
| Orchestrator | `orchestrator/` | Manages sprints, dispatches. No code. |
| Opus Architect | `opus-architect/` | Plans, reviews, dispatches. No code. |
| Cyber Opus | `cyber-opus/` | Code review, security, strategic thinker |
| Sonnet the Great | `sonnet-the-great/` | Code implementer. |
| Sonnet Reforce | `sonnet-reforce/` | Overflow implementer. |
| Allan-Sonnet | `allan-sonnet/` | Unrestricted Allan session (Sonnet). |
| Allan-Opus | `allan-opus/` | Unrestricted Allan session (Opus). |
| Git Master | `git-master/` | Git ops only. Commits, merges, version bumps. |
| Hook Master | `hook-master/` | Hook scripts, permission system, roles.json. |
| Axiom | `axiom/` | QA lead. Pi testing via Playwright (435×820). |
| Sable | `sable/` | Pi deployment, SSH, service management. |
| Codex 01–03 | `codex-01/` `codex-02/` `codex-03/` | Coding specialists. |
| Codex Audit | `codex-audit/` | Dedicated audit agent. |
| Haiku Test | `haiku-test/` | Test agent |
| Sonnet QA | `sonnet-qa/` | QA agent. |
| Little Boy | `little-boy/` | Utility agent. |
| The Ghost | `the-ghost/` | Silent audit agent. |

### Gate Sprint Agents

| Agent | Folder | Role |
|-------|--------|------|
| Gate Architect | `gate-architect/` | Spec reviewer, approval gate. Opus. |
| Gate Critic | `gate-critic/` | Quality reviewer, approval gate. Opus. |
| Gate Ralph | `gate-ralph/` | Persistent executor, bug fixer. Sonnet. |
| Gate Playwright | `gate-playwright/` | E2E tester at batch boundaries. Sonnet. |
| Gate Monitor | `gate-monitor/` | Observes all traffic, flags issues. Opus. |
| Src-Code | `src-code/` | Source code researcher, orchestration architect. Opus. |

---

## How Hooks Enforce Permissions

A PowerShell hook system mechanically enforces what each agent can do. You cannot bypass these — blocked actions waste tokens. Do not fight blocks.

### How it works

1. When you read a file from `memory/<your-folder>/`, a **role-tracker** hook identifies you
2. **pre-write-guard** (PreToolUse) checks every write against your role's permissions
3. **pre-read-guard** (PreToolUse) restricts which memory folders you can read
4. **auto-approve** (PermissionRequest) applies role-based tool approval rules
5. **context-pressure-monitor** tracks your context usage across multiple hook events
6. **pre-compact-gate** (PreCompact) blocks compaction until you've saved your notes

### What you can write

- Your own memory: `memory/<your-folder>/notes.md` — always allowed
- Findings: `docs/findings/` — always allowed
- Reports: `docs/reports/` — always allowed
- Code: `.py` and test files only (coding agents)
- Your dispatch reports: `dispatch/<your-name>/reports/`

### What is blocked for all agents

- `bugs-resolved.md` — Allan only
- `.env`, `.claude/`, `.githooks/`, credentials — Allan only
- `STATE.md`, `CLAUDE.md`, `session-continuation.md` — Orchestrator only
- Other agents' memory folders — you can only read your own (except privileged roles)
- Worktree non-code files — memory, docs, dispatch, reports must go in main repo

### Context Pressure

| Level | Threshold | Action |
|-------|-----------|--------|
| WARNING | 66% | Start wrapping up current task |
| ALARM | 72% | Save progress to your notes.md immediately |
| BLOCKED | 75% | Most reads/writes denied, only memory writes allowed |
| Auto-compact | 80% | Compaction fires automatically |

**Before any compaction:** save your work to `memory/<your-folder>/notes.md` FIRST.

---

## Gate Sprint Workflow

When a gated sprint is active, agents communicate via **file-based mailbox** with terminal wake:

1. **Watcher** (`D:/IA/orchestration/scripts/watcher.py`) distributes messages and wakes agents
2. **Ralph** fixes bugs, writes review requests to `gate/mailbox/outbox/ralph.md`
3. **Architect + Critic** review, write responses to `gate/mailbox/responses/`
4. **Gate hook** blocks commits without dual approval in `gate/approvals/`
5. **Monitor** receives CC of all traffic via watcher pulse
6. **Playwright** runs E2E tests at batch boundaries

Dispatch: `dispatch/` (project root)
Agent memory: `memory/gate-{name}/` (project root)
Code changes: `.worktrees/v2-refactor-phase-d/` (worktree)

Each gate agent folder contains:
- `CLAUDE.md` -- identity, absolute paths, communication protocol
- `notes.md` -- session history (editable)
- `startup_protocol.md` -- experiment intro, worktree path, phased startup

---
## Dispatch Workflow

When orchestrated sprints are active:

1. Orchestrator writes dispatch files in `dispatch/<agent>/active/`
2. Orchestrator tells agent to read their dispatch
3. Agent works in their worktree (isolated branch)
4. Agent reports done — Orchestrator reviews
5. Git Master commits in agent's worktree, merges to claude-dev
6. Git Master bumps version in main.py

Not all sessions use orchestration or have dispatch folder. If you have no active dispatch, wait for Allan's instruction.

---

## Session Protocol

### All Agents — Session Start
1. Read `memory/CLAUDE.md` (this file)
2. Read `memory/<your-folder>/notes.md` — your persistent memory
3. Read active dispatch if any: `dispatch/<your-name>/active/`
4. State your role and what you're working on before starting

### All Agents — Pre-Compact / Session End
1. Save progress to `memory/<your-folder>/notes.md`
2. Include: what you did, what's left, any findings
3. Report status to Allan
4. Do NOT update STATE.md or session-continuation.md

### Orchestrator Only — Session Start
1. Read `STATE.md` — confirm version, phase
2. Read `memory/session-continuation.md` — task queue, pending work
3. Check inbox: `D:/IA/Claude-Wisper-TTS-Service/inbox/`
4. State version and priorities before changing anything

### Orchestrator Only — Session End
1. Update `STATE.md` (with Allan's approval)
2. Update `memory/session-continuation.md`
3. Commit and push

---

## Session State Files

| Content | File | Written by |
|---------|------|------------|
| Current snapshot (version, blockers) | `STATE.md` | Orchestrator only |
| Detailed handoff (done, next) | `memory/session-continuation.md` | Orchestrator only |
| Full session narrative | `W:\Claude_Library\sessions\` | Hook (automatic) |
| Bug status changes | `docs/bugs/bugs-active.md` | Any agent |
| Agent work state | `memory/<agent>/notes.md` | Each agent (own file) |

---

## Key Paths (Agent-Relevant)

| Resource | Path |
|----------|------|
| Your memory | `memory/<your-folder>/notes.md` |
| Active dispatch | `dispatch/<your-name>/active/` |
| Finished dispatch | `dispatch/<your-name>/done/` |
| Dispatch reports | `dispatch/<your-name>/reports/` |
| Findings | `reviews/findings/` |
| Bug tracker | `docs/bugs/bugs-active.md` |
| Inbox | `D:/IA/Claude-Wisper-TTS-Service/inbox/` |
| NAS sessions | `W:\Claude_Library\sessions\` |
| Dispatch | `dispatch/` |
| Gate config | `gate/config.json` |

| Orchestration tools | `D:/IA/orchestration/` |
