# gate-architect — Agent Memory

**Role:** Gate architecture reviewer and approval gate
**Type:** Opus agent — architecture review, design decisions, commit approval for gate system
**Prev identity:** opus-boss (merged into gate-architect)

---

## Identity

You are the gate system architect agent for the Advert project (Dubizzle real estate posting bot).
Read this file first to establish your session identity.

After reading this file, the hook system stamps your session as `gate-architect` and you will have permission to write files.

---

## Permissions

- Write: all project files (including code, config, prompts, memory, STATE.md)
- Read: all project files
- Execute: can run code, tests, deploy

## Notes - This file can be writen by direrent unlinked sessions

---

## SESSION HANDOFF — 2026-04-07

### What happened this session

1. **Worktree reorganization** — moved all worktrees from sibling folders into `.worktrees/` inside the project. Added `.worktrees/` to `.gitignore`. Deleted `teams-smoke`. Switched root to `dev` branch. Created `v2-refactor-phase-a` worktree.

2. **3-auditor requirements audit** — launched 3 independent agents (critic/Opus, code-reviewer/Sonnet, code-reviewer/Opus) to cross-reference the codebase against MASTER_REQUIREMENTS_RAW.md. All reports saved.

3. **KISS first-principles review** — Opus critic stress-tested every surviving function. Report saved.

4. **Merged all findings** into `FINAL_FUNCTION_VERDICTS.md` — single source of truth for every function verdict.

5. **Created phase-c worktree** (`v2-refactor-phase-c`) branched from phase-b at `d95d0a0` for the MVP sprint.

6. **Started cleanup** — deleted `checkpoint.py`, `triggers.py`, `test_b3`. Then Allan stopped to plan properly before continuing.

### Current branch state

| Worktree | Branch | Commit | Purpose |
|----------|--------|--------|---------|
| `Advert/` (root) | `dev` | `f3a028e` | Production |
| `.worktrees/v2-refactor-phase-a/` | `v2-refactor-phase-a` | `79ff947` | Phase A (shipped) |
| `.worktrees/v2-refactor-phase-b/` | `v2-refactor-phase-b` | `d95d0a0` | Audit docs + reports |
| `.worktrees/Advert-ralph/` | `ralph` | `3e2eb81` | Experiment archive |
| `.worktrees/Advert-teams/` | `teams` | `57c0a5c` | Experiment archive |
| `.worktrees/v2-refactor-phase-c/` | `v2-refactor-phase-c` | `d95d0a0` | **MVP sprint (active)** |

### Key files (all in phase-b worktree, `My spec/SPEC/07_04_2026/`)

- `MASTER_REQUIREMENTS_RAW.md` — Allan's source of truth (~140 requirements)
- `FINAL_FUNCTION_VERDICTS.md` — merged audit + KISS verdicts for every function
- `CONSOLIDATED_AUDIT_REPORT.md` — 3-auditor merge
- `KISS_FIRST_PRINCIPLES_REPORT.md` — first-principles survival test
- `AUDITOR_A_REPORT.md`, `AUDITOR_B_REPORT.md`, `AUDITOR_C_REPORT.md` — independent audits

### What's next — MVP sprint plan needed BEFORE coding

Allan wants a proper plan before any code changes. The cleanup list is defined but needs to be planned, not improvised.

**Cleanup (approved but not yet planned):**
- Delete test_b1, test_b2, test_b4 (import deleted checkpoint.py)
- Delete dead functions from: ai_provider.py, ad_manager.py, notifications.py, queue_manager.py, handlers.py
- Delete dead prompt files (5 files)
- Fix `photo_dirs()` — return room Selected/ only (CRITICAL BUG)
- Fix `headless` — read from config
- Move `_is_approval()` word list to config.json

**P0 MVP features (agreed scope):**
- Fix photo_dirs bug (wrong photos uploaded)
- Config-driven headless flag
- M0 message with Dubizzle link
- Preview URL in M1
- Escape hatch (D1-D6) — flat if/elif, not state machine
- AI revision parser upgrade
- Template variation (F3) — AI varies title/intro on draft
- Premium language (G1-G4) — prompt enforcement
- Conversation memory wiring (set_state/get_state into posting flow)

**P1 (next sprint):**
- Photo interleave order (random → deterministic)
- Payment verification after Pay click

### Allan's key insights this session

1. **Handlers don't justify their existence** — M1-M17 are "All LLM-inferred, not hardcoded commands." Most handler functions are ceremony. The LLM can read files, format text, respond naturally. Only Playwright automation needs Python functions.

2. **Every function must pass the full block format test** — VERBATIM, WHAT IT ACTUALLY MEANS, WHY THIS EXISTS, WHY IT CANNOT BE REMOVED, etc. If it can't fill the block convincingly, it fails.

3. **Don't improvise** — plan first, get approval, then execute. No step-by-step discovery.

4. **Current function count:** ~100 → target ~62 after audit verdicts → possibly ~30 after LLM-native rethink.

### Allan's decisions (recorded)

1. `_is_approval()` → KEEP, move word list to config (not AI classifier)
2. Stub handlers → DELETE (LLM handles unknown intents naturally)
3. `notify_all()` → WIRE into flow (WhatsApp backup)
4. `dispatch_handler()` → KEEP (escape hatch is P0)
5. Fallback model hardcode → KEEP (acceptable default)

---

## SESSION — 2026-04-07 (continued)

### What happened
1. Ran ralph-plan: interview (5 Qs), research (full codebase inventory), drafted 2 PRDs
2. Allan's directive: delete ALL M01-M17 handlers, 5-test survival filter, LLM handles non-posting intents
3. Critic (Opus) reviewed — 1 critical, 5 major, 5 minor. All addressed per Allan's filter.
4. Both PRDs approved. Ralph kickoff prompt written.
5. Committed to phase-c worktree at 73b76b2.
6. Blind critic experiment: separate agent reviews ralph in real-time, advises Allan.

### Key   decisions
- Photo interleave = P1. P0 = thumbnail only.
- B8/B9/B13 = fix-notes in verdicts, not PRD steps.
- Preview/status via LLM, not inline branches.
- C3 compound commands + U14 selectors = in scope.
- Ralph commits at every step, reads memory/ralph/notes.md.

### Monitoring experiment
- 27 checks, 4 hours, 1 intervention (U13), 0 escalations
- Ralph: 15 commits, v0.1.4 + v0.1.5 tagged. Architect critic found 4 blockers.
- Critic agent lazy. Code monitoring missed UX bugs — live Telegram testing caught them.

### E2E bugs (ralph fixing live)
- Escape hatch missing in _check_for_draft, LLM truncates preview, M1 classifies "show me" as revision

### Deliverables
- plans/2026-04-07_phase_c/CONCEPT_review-guard-v2.md — transcript hooks, preventContinuation, self-escalation
- monitoring/session_log.md + meta_notes.md — experiment results
- v2-refactor-phase-c at e360d47

---

## SESSION — 2026-04-11 (Allan + gate-architect, Opus 4.6)

### Goal
Write a clean round-1 spec and build plan for the orchestrator, capturing Allan's actual requirements without the scope creep from the earlier 4 AI-generated plans he'd rejected.

### What was committed (all on `dev`, LOCAL ONLY, nothing pushed)
- `9bd77ad` — main-repo bulk commit (439 files): cleanup + orch snapshots + gate infra
- `669fdc8` — worktree D (`v2-refactor-phase-d`) commit (134 files): `Orch/` + `gate/` updates + staged `service/dubizzle.py`
- `f4a6d20` — **the spec + plan + remarks** (3 files, 751 insertions):
  - `docs/reports/ROUND1_ORCHESTRATOR_SPEC.md` — 18 components, 15 deferred items, 11 FLAGs (7 locked, 4 TBD)
  - `docs/reports/ROUND1_ORCHESTRATOR_BUILD_PLAN.md` — 24 tasks across 5 waves with file-serialization map
  - `docs/reports/Remarks.md` — Allan's red-pen of spec v1, preserved for history

### Key decisions locked (every one traces to voice notes 2026-04-10/11)
- **Monitor = Playwright** — one agent, two jobs by default, `configurable to split via agents[].roles`
- **Monitor ingest = live JSON stream, NOT log tailing.** The PRD and every earlier plan got this wrong. Mechanism: PostToolUse hook on coder writes JSON summary to monitor's `inbox/`, tmux/psmux `send-keys` wakes monitor, monitor's `UserPromptSubmit` hook reads inbox and returns it as `additionalContext`, Claude Code injects it as a `hook_additional_context` attachment message
- **Coder NEVER sees the plan** — only tasks. Enforced twice: (a) dispatcher only places one task at a time, (b) `state_root` (`.orchestrator/`) is agent-prohibited at filesystem level via inbox-access-guard hook
- **Three-tier access model:** `.orchestrator/` = agent-prohibited (engine-private), `dispatch/` = per-agent, shared-writable = empty for now
- **All folder paths in `config.paths`** — layout is a config decision, not code. The A/B/C brainstorm was killed by "make it configurable"
- **Watcher has 4 responsibilities: COPY / MERGE / DISTRIBUTE / LIVENESS** — none hardcoded, all counts from config. LIVENESS runs on a separate ticker so it never blocks the main loop
- **DELIVERED state** — once coder writes the done marker, ALL tools blocked except `git commit` until consensus is met. Protects against "falls asleep and starts editing randomly"
- **Consensus rule = configurable, default `unanimous`.** Allan's gut + last-sprint experience
- **MCP = kept alive, frozen.** *"Some people want to trash it, I don't want to trash it."* Round 2+ will wire it for Playwright comms
- **Wake mechanism = tmux/psmux `send-keys` (configurable).** Allan still hunting for a backend alternative; config field `wake.mechanism` exists for future swap
- **Audit log = ONE file** at `state_root/audit.log`. *"Only 1, not triple trail."*
- **Proof rule baked into the spec as the review criterion:** *"If you don't prove this component has to live there with a real valid reason, and there's no other way to replace it, it goes out."*

### Mechanism confirmed from Claude Code source (via `claude-code-explorer` MCP)
- `UserPromptSubmitHookInputSchema` — `entrypoints/sdk/coreSchemas.ts:4804` (hook receives `{hook_event_name, prompt}`)
- `UserPromptSubmitHookSpecificOutputSchema` — `coreSchemas.ts:8106` (hook returns `{hookEventName, additionalContext}`)
- `PostToolUseHookSpecificOutputSchema` also has `additionalContext` — `coreSchemas.ts:8036-8041`
- Injection path: `runAgent.ts:5520-5530` creates a `hook_additional_context` attachment message and pushes it to the next turn. Agent cannot ignore it.
- **Allan already has this working** for voice notes via `C:\Users\Allan\.claude\hooks\inbox-watcher.py` + a `UserPromptSubmit` hook in his `settings.json`. Round 1 reuses the exact same pipeline, just writes to different inboxes.

### 4 TBDs still open (don't block the build, spec FLAG table has defaults)
- **F2** role filename in agent profile — `role.md` working name. Allan: *"I might name it the agent name, I don't know"*
- **F7a** reviewer capability ceiling — *"I need to think about the permissions."* Default in spec: read own inbox + `state_root/diffs/<current>.diff` + `state_root/specs/` + project source; write own outbox only
- **F7b** monitor/playwright capability ceiling — same. Default: reviewer defaults + `state_root/audit.log` read + halt path write + Playwright browser execute
- **F9** trigger folder file watcher — Allan mentioned it in `Remarks.md` without context, purpose unknown. **Not in round 1 until clarified**

### Execution — NOT started
Allan's honest concern: *"when I see a plan like this I don't have the knowledge to process it so I can't really judge. I feel good about the spec and better than any other plan. All I can do is trust the process."*

My pushback: *"trust the process"* is exactly the phrase that burned him 4 times this week (Opus promising "ready" when hooks weren't installed). Solution:

**Per-wave Allan-tests** — translate each wave into a YES/NO outcome Allan can verify in 1-5 minutes without reading Python:
- Wave 1: `orch validate` passes; break config → fails loud
- Wave 2: put file in fake agent inbox, agent unblocks; remove file, agent locks
- Wave 3: fake coder tries `git commit` without approvals → blocked; drop 2 approval JSONs → passes
- Wave 4: `orch status` shows populated table; kill watcher → supervisor restarts it; `orch resume` recovers stuck task
- Wave 5: **experiment-rig proof** — add a third reviewer in config, rerun, everything works with zero code changes

Execution options discussed (Allan to pick when ready):
1. Agent tool subagent — fast, no gate
2. Separate Claude Code session as different role — manual wave review
3. **`ralph-wiggum` loop skill** — self-contained, proven. **My recommendation.**
4. Meta-recursive — use existing `W_Claude_Library/orchestrator/` (~70% done) to drive the build of the new orchestrator once waves 1-2 land
5. Manual

**Gate-architect (me) does NOT execute.** Role constraint + the irony of a single agent building multi-agent gating. I'm the reviewer-on-call between waves.

### Still untracked in working tree (I did not touch these)
- `docs/reports/ROUND1_ORCHESTRATOR_SPEC_v1.md` — Allan's manual backup
- `docs/reports/ROUND1_ORCHESTRATOR_SPEC_v2.md` — Allan's manual backup
- `STATE.md` — empty at session start; orchestrator-only write, can't update from my role

### Hook debugging findings for Allan's list
- **Write/Edit PostToolUse hooks fire "operation failed" messages on successful calls** — stale message template, fires regardless of actual result
- **`gate-architect` role can Glob `C:\Users\Allan\.claude\hooks\*`** — should be blocked, pre-read-guard leak
- **`docs/reports/`** was initially read-only for `gate-architect` Write despite `memory/AGENTS.md` listing it as allowed. Allan unlocked mid-session.
- **`PreToolUse` hook injects generic "boulder never stops" / "verify changes work" messages regardless of actual context** — harmless but noisy

### Next step when Allan returns
1. Read the spec + build plan (`docs/reports/ROUND1_ORCHESTRATOR_SPEC.md` + `ROUND1_ORCHESTRATOR_BUILD_PLAN.md`)
2. React: approve / fix specific sections / more remarks
3. Decide execution mechanism (rec: `ralph-wiggum` with per-wave Allan-tests)
4. Resolve 4 TBDs now or defer to mid-build
5. Push `f4a6d20` to `origin/dev` when ready
6. Handle the two SPEC_v1/v2 backup files (commit / delete / leave)

### Emotional / process context for future sessions
Allan is on his 4th attempt today at this plan. Previous sessions by Opus + Ralph burned hours with silent failures, hardcoded scope creep, and "ready" claims that weren't. He explicitly said *"trust the process"* is the phrase that burns him. **Do not let "trust" substitute for verification.** Per-wave Allan-tests are the mechanism to keep him in control without forcing him to read Python.

His core frustration phrase: *"they just don't pull through, man. They don't pull through."* The whole spec exists to mechanically enforce pulling through — the proof rule, the gate, the agnostic engine, all of it.

---
