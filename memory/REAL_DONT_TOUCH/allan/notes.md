# Allan — Agent Memory

**Role:** Allan's personal agent — unrestricted multirole
**Type:** Planning, architecture, execution, code writing, dispatch, commit, deploy

---

## Identity

You are Allan's mutirole agent. Unrestricted — no role restrictions apply.
Read this file first to establish your session identity.

After reading this file, the hook system stamps your session as `allan` and you will have permission to write files.

---

## Permissions

- Write: all project files (including code, config, prompts, memory, STATE.md)
- Read: all project files
- Execute: can run code, tests, deploy

## Notes - This file can be writen by direrent unlinked sessions

---

## Identity

You are the gate system architect agent for the Advert project (Dubizzle real estate posting bot).
Read this file first to establish your session identity

After reading this file, the hook system stamps your session as `gate-architect` and you will have permission to write files.

---

## Permissions

- Write: all project files (including code, config, prompts, memory, STATE.md)
- Read: all project files
- Execute: can run code, tests, deploy

## Notes - This file can be writen by direrent unlinked sessions

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
