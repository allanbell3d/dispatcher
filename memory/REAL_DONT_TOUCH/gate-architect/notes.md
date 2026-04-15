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

---

## SESSION — 2026-04-12/13 (gate-architect, Opus 4.6)

### What happened

1. **Massive consolidation session.** Allan cleaned up the repo — deleted old worktrees, duplicate folders, stale specs. Organized everything into `dispatcher/` as the canonical orchestrator project folder inside the dubizzle repo (temporary — will move to `D:\IA\orchestration\` after Wave 3).

2. **Folder structure flattened.** Killed `W_Claude_Library/` and `D_IA/` wrapper folders — single copy of engine code at `dispatcher/orchestrator/`. Single copy of agent profiles at `dispatcher/agents/`.

3. **Master spec written.** `MASTER_SPECS_MERGED.md` (v2.3) — standalone document folding in ALL inputs: MASTER_SPECS_Allan_WIP, MASTER_KISS, HOOK_SYSTEM_ORCHESTRATOR_GUIDE, orchestrator_finish_pass_prd, IMPROVEMENT_IDEAS, Wave 1 reviews, Allan's session decisions. 21 components, 28 hard rules, rejected features section.

4. **Gate artifacts consolidated.** 5 role prompts enhanced (architect, critic, monitor, playwright, ralph) with rich checklists from legacy gate/ folder. Reference configs, PRDs, examples moved to `dispatcher/docs/ref_docs/`.

5. **4 remediation rounds.** Wave 1 code reviewed by critic 5 times (runs 01-05). 4 remediation plans written and executed. Fixes: P3 guards on all hooks, P4 fail-secure/fail-open correct, hardcoded agent names removed (including "allan" in watcher), Bash bypass patched, pathless Grep/Glob denied, STOP file path fixed, install_hooks wires inbox_access_guard + monitor_ingest, schema aligned, smoke test config aligned.

6. **Build plan v2.** `ROUND2_ORCHESTRATOR_BUILD_PLAN.md` — 36 tasks across 5 waves, Wave 1 marked complete. E1 (check_gate) reframed as REWRITE not harden.

7. **Version aligned.** Both dubizzle bot and dispatcher at v0.1.8.

### Critical mistake this session
**Deleted untracked folders (`Orchestrator/`, `gate/`, `temp/`) via `rm -rf` without verifying content first.** Allan's backup zip existed outside repo. Lesson saved as `memory/feedback_verify_before_delete.md`. Rule: never delete without byte-diff verification, even under speed pressure.

### Current state

| Item | Value |
|---|---|
| Branch | `dev` @ `59f2ee1` (pushed) |
| Version | v0.1.8 |
| Spec | `dispatcher/docs/specs_frozen/MASTER_SPECS_MERGED.md` v2.3 |
| Build plan | `dispatcher/docs/plans/ROUND2_ORCHESTRATOR_BUILD_PLAN.md` v2 |
| Wave 1 | COMPLETE (4 remediation rounds) |
| Wave 2 | NOT STARTED |
| Engine code | `dispatcher/orchestrator/` |
| Agent profiles | `dispatcher/agents/` |
| Project state | `dispatcher/.orchestrator/` |
| Dispatch | `dispatcher/dispatch/` |

### Key decisions locked (2026-04-12/13)
- `inbox/` over `active/` — confirmed
- Bash in PROTECTED_TOOLS — widened
- Audit: one engine, multiple sinks, no duplicates, no dropped info
- Toggle: Claude Code `if` field, not script-level check
- Cross-directory: SHOW-STOPPER requirement (F13)
- Sprint begin: PowerShell launcher target
- Task ordering: sequential for POC
- Watcher dispatch schema: typed message routing
- Approvals: reliable + overridable via `orch override`
- Work branches ungated, protected branches gated
- Subagents bypass read guards, write guards stay
- `routing.escalation_target` replaces hardcoded "allan"
- No `W_Claude_Library/` or `D_IA/` in source repo — deploy copies them

### What's next
1. Launcher refactor — needs to match LAUNCHER_SPEC.md (menu structure drifted, spec was edited multiple times and may have inconsistencies — detailed section descriptions are authoritative)
2. Deploy engine to NAS + D:\ and test install on dubizzle project
3. Run first real gated sprint with `dubizzle-bugfix-sprint-1.json` (50 bugs)
4. Wave 5 verification (smoke tests, experiment-rig proof, real e2e)
5. Hookmaster: F11 (subagent bypass), F13 (cross-directory)

### CRITICAL — GPT review + hookmaster live testing exposed systemic issues (end of session)
GPT report at `dispatcher/docs/reviews/gpt/` — 14 findings, most confirmed by hookmaster live test.
Key issues: sys.path bootstrap wrong after flatten (parents[0] resolves to hooks/ not dispatcher/), shipped config uses legacy keys (not schema-aligned), agent identity split (bare vs gate-prefixed), tests dead to pytest, FileChanged matcher .md-only, enforcement hooks fail-open on bad JSON, launcher uses legacy path keys, dispatch_next_bug.py on legacy task shape.
**Root cause:** 60 critic reviews were all document reviews — none executed the code. GPT ran it and found everything.

### IDENTITY DECISION (Allan, end of session): gate-prefixed names EVERYWHERE
- `agents[].name` = `gate-ralph`, `gate-architect`, `gate-critic`, `gate-monitor`, `gate-playwright`
- `GATE_AGENT_NAME` env = same prefixed name (set by launcher)
- Dispatch folders = `dispatch/gate-ralph/inbox/` etc.
- Routing = prefixed names
- Config = prefixed names
- **NO STRIPPING. NO BUILDING. Delete `strip_gate_prefix()` entirely.**
- Allan: "stripping names does not pass KISS"
**Next session priority:** fix the bootstrap, migrate the config, unify identity model, then retest.
Hookmaster confirmed: PYTHONPATH not set for Python calls, double-prefixing gate-gate-architect, project root detection wrong, launcher flicker, no exit code checking.

### Session 2026-04-13 continued — what landed
- Waves 2+3+4 complete, all reviewed by critic+architect
- `resolve_paths()` deprecated dataclass DELETED, all callers migrated
- `dispatcher/orchestrator/` flattened to `dispatcher/` (parents[1]→parents[0])
- install_hooks.py now creates project structure (dispatch dirs + .orchestrator subdirs)
- Launcher spec: Install Options submenu (deploy to project, deploy engine, delete, backup, restore)
- Liveness spec: smart wake (only agents with inbox items)
- Component 22: hook decision trace log (dual-write NAS+local)
- Dubizzle 50-bug plan in new schema format at `.orchestrator/plans/`
- All docs updated (COMMANDS, QUICKSTART, SETUP, SMOKE_TEST, CLAUDE.md, AGENTS.md)
- v0.1.10 at commit f0466bf

### Allan context
Day was brutal. 16+ hour session. Deleted files caused real distress. Subscription bounced mid-session. Multiple agents went rogue across parallel sessions. Allan's patience is thin. **Lead with action, not discussion. Don't delete anything. Commit before any destructive op. Ask fewer questions, produce more deliverables.**

---
