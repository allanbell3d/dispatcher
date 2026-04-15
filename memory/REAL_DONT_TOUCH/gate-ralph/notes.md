# gate-ralph — Agent Memory

**Role:** Gate persistent executor
**Type:** Sonnet agent — bug fixing, feature implementation, persistent task loops for gate system
**Prev identity:** ralph (merged into gate-ralph)

---

## Identity

You are the gate system Ralph (persistent execution) agent for the Advert project (Dubizzle real estate posting bot).
Read this file first to establish your session identity.

After reading this file, the hook system stamps your session as `gate-ralph` and you will have permission to write files.

---

## Permissions

- Write: all project files
- Read: all project files

## Notes - This file can be written by different unlinked sessions


### Session 2026-04-09
 
- **Allan** Setup orchestator

---

## Merged from ralph — Session 2026-04-07 (Phase C MVP Sprint)

- Executed PRD-1 (cleanup) + PRD-2 (P0 features) as ralph --critic=architect
- **28 commits** on `v2-refactor-phase-c` branch (06adcc7 → 1f41a4d)
- Merged to dev at `a74fd42`

**PRD-1 (7 commits):** deleted 3 dead files (~2,470 lines), 10 dead functions, 17 inlines, photo_dirs critical bug fix, config-driven hardcodes, orphaned prompts deleted

**PRD-2 (7 commits):** handler collapse 17→3, LLM response path, M0/M1 checkpoints, escape hatch D1-D6, template variation with hard-fact verify, conversation memory, payment B8/B9/B13

**Post-test fixes from Allan's live testing (14 commits):**
- Full ad text in context, M0 sends real browser URL, M0/M4 fire-and-forget
- Photo re-upload during M1 review, D3/D4 keyword matching
- Phone number revision, safety check for non-ad AI output
- Edit path creates dated copy, hard-fact warning on edit
- Daily-rotating file logging, honest photo count

---

### Session 2026-04-08 — QA Testing + Merge to Dev

**What happened:**
- Tested bot live via Playwright MCP on Telegram Web (sent messages, read responses, checked Dubizzle form)
- Found and fixed 5 bugs (commit `ae659f9`): phantom waiter after cancel/error, Playwright _close() crash, photos undefined, result unbound
- **Full QA pass: 50 bugs found** — written to `QA_BUG_REPORT_2026-04-08.md`
- Added `__version__ = "0.1.6"` to bot.py + changelog entries for 0.1.3-0.1.6 (commit `55a6253`)
- **Merged v2-refactor-phase-c → dev** at `a74fd42`, pushed to remote
- Created `.worktrees/v2-refactor-phase-d/` on branch `v2-refactor-phase-d` for next iteration

**Key QA findings (top bugs):**
- B1/B2: Fresh form fills nothing (no wait after category selection)
- B3: Description selector picks title textarea (`.first` on union selector with `textarea` fallback)
- B4: Title doubled on draft resume (React `.fill()` appends)
- B5: "No price set" notification creates phantom waiter (wait=True inside try block)
- B10/B11: change_price and edit_ad modify "live" files directly — no dated copy for real-dated files
- B12/B13: AI edit adds **Room:**/**Villa:** metadata, corrupts template format
- B15: Timezone bug — dated copies use UTC not Dubai time
- B17: Body price not updated when header price changes

**Allan's feedback this session:**
- "Don't jump to fixing code — test thoroughly first, collect ALL findings, present for review"
- "Test every combination of language, every field, stress test with partial data"
- "50 bugs, not 50 tests"
- Stay on 0.1.x — 0.2 after bugs ironed out

**Phase D concepts read (from D:/IA/claude-code-src/):**
- REVIEW-GUARD-RESEARCH.md — native Claude Code mechanisms (hooks, SendMessage resume, FileChanged watcher)
- CONCEPT_review-guard-v2.md — preventContinuation + SendMessage, transcript reading, self-escalating hooks
- CONCEPT_mcp-powered-review-guard.md — claude-code-explorer MCP for self-validating supervisors
- These are IDEAS, not plans. Need to figure out what actually works for Phase D.
- claude-code-explorer MCP is installed globally but didn't load in this session (needs restart)

---

## Merged from ralph — Session 2026-04-07 (Phase C MVP Sprint)

- Executed PRD-1 (cleanup) + PRD-2 (P0 features) as ralph --critic=architect
- **28 commits** on `v2-refactor-phase-c` branch (06adcc7 → 1f41a4d)
- Merged to dev at `a74fd42`

**PRD-1 (7 commits):** deleted 3 dead files (~2,470 lines), 10 dead functions, 17 inlines, photo_dirs critical bug fix, config-driven hardcodes, orphaned prompts deleted

**PRD-2 (7 commits):** handler collapse 17→3, LLM response path, M0/M1 checkpoints, escape hatch D1-D6, template variation with hard-fact verify, conversation memory, payment B8/B9/B13

**Post-test fixes from Allan's live testing (14 commits):**
- Full ad text in context, M0 sends real browser URL, M0/M4 fire-and-forget
- Photo re-upload during M1 review, D3/D4 keyword matching
- Phone number revision, safety check for non-ad AI output
- Edit path creates dated copy, hard-fact warning on edit
- Daily-rotating file logging, honest photo count

