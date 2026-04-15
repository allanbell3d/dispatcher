# gate-critic — Session Notes

**Role:** Quality reviewer and approval gate
**Model:** Claude Opus

---

## Do NOT save reports in this folder

- Private folder — identity assignment
- Read/write protected — only you can access
- Reports go to `dispatcher/docs/reviews/`

## Notes — this file can be written by different unlinked sessions

### Session 2026-04-07 — Live Monitoring Experiment (Phase C)

**What happened:** Critic monitored ralph executing PRD-1 (cleanup) + PRD-2 (P0 features) live. 28 commits. Zero scope creep. PRD-1→PRD-2 architect review gate worked. Allan did real QA via Telegram.

**Bugs found during live test (Allan caught, not agents):**
- U13: Hardcoded checkpoint messages — commit said "config-driven" but code still had inline f-strings
- Draft detection escape hatch broke on "show me"
- "Leave as draft" / "cancel posting" not understood during M1
- LLM summarized ad text instead of returning verbatim (fixed 041cbc7)
- Photos: 16 uploaded when max_photos config is 10

**What worked in monitoring:**
- JSONL parsing for ralph's tool calls
- Git log commit-by-commit tracking
- 4-question survival filter as AC gate
- Architect review gate between PRDs caught 2 blockers

**What failed:**
- No Telegram monitoring until Allan told me to open it — missed all UX bugs
- Pane capture useless (ralph not in tmux)
- Assumed config.json wasn't in worktree (it was)
- Neither critic nor architect caught U13 — Allan was the only real gate
- 90s polling too slow — 30s was right

**Lesson:** Agents missed what mattered. Allan caught what mattered. The gate system is only as good as what the reviewers actually check. Read the code, don't assume from summaries.
