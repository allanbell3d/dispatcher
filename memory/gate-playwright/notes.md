# gate-playwright — Agent Memory

**Role:** Gate Playwright testing agent
**Type:** Sonnet agent — Playwright browser automation, E2E testing for Dubizzle posting bot

---

## Identity

You are the gate system Playwright testing agent for the Advert project (Dubizzle real estate posting bot).
Read this file first to establish your session identity.

After reading this file, the hook system stamps your session as `gate-playwright` and you will have permission to write files.

---

## Permissions

- Write: reports, own notes
- Read: all project files

## Notes - This file can be written by different unlinked sessions

---

## Prior Playwright testing — QA Bug Report 2026-04-08

Ralph (Opus) ran the first Playwright-on-Telegram-Web QA pass. Full report:
- **File:** `reports/QA_PLAYWRIGHT_BUG_REPORT_2026-04-08_phase_C.md`
- **Tester:** Ralph via Playwright MCP on Telegram Web
- **Commit tested:** `ae659f9` on `v2-refactor-phase-c`
- **Result:** 50 bugs found (9 critical, 12 high, 15 medium, 14 low)

### Critical bugs found (B1-B9)
- B1/B2: Fresh form fills nothing — no wait after category selection, DOM not rendered
- B3: Description selector grabs title textarea (`.first` on union selector)
- B4: Title doubled on draft resume (Playwright `.fill()` appends in React inputs)
- B5: "No price set" creates phantom waiter (`wait=True` inside try block)
- B6: PermissionError crashes error handler (`os.replace` on locked file)
- B7: edit_ad_copy blocks main poll thread (sync AI call, 30-60s unresponsive)
- B8: Price validation after browser launch (waste: AI call + dated copy for nothing)
- B9: Batch cancel only cancels first room

### Key testing lessons
- Open Telegram Web at session START, not after bugs are found
- Test fresh form AND draft resume paths — completely different code paths
- Batch operations need individual cancel verification
- React-controlled inputs need special clear-before-fill handling
- File locking on Windows causes intermittent crashes — test with concurrent operations

### Known test targets
- Telegram Web bot interaction (message sending, response validation)
- Dubizzle form: category selection, title, description, price, photos
- Photo upload flow (max_photos enforcement, thumbnail selection)
- Escape hatch commands (D1-D6)
- Draft/publish/cancel flows
- Language variations (English/Arabic)
- Batch posting (multi-room)
- Price change / edit flows on live files vs templates
- `gate/tasks.json` — 50 bugs with acceptance criteria



## Merged — Session 2026-04-08 (QA + Merge)

- Tested bot live via Playwright MCP on Telegram Web
- Found and fixed 5 bugs: phantom waiter, Playwright _close() crash, photos undefined, result unbound
- **Full QA pass: 50 bugs found** — written to `QA_BUG_REPORT_2026-04-08.md`
- Version bumped to 0.1.6, merged phase-c → dev, phase-d worktree created

**Known remaining issues:**
- AC35: dubizzle.py still has user-facing f-strings
- No "moderating" conversation state transition after M4
- Sonnet model quality for edit_ad_copy worse than Opus

**Allan's feedback:**
- "Don't jump to fixing code — test thoroughly first, collect ALL findings, present for review"
- Stay on 0.1.x — 0.2 after bugs ironed out