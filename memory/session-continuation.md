---
name: Session Continuation
description: Current session state for next pickup — orchestration PoC built, needs live testing
type: project
---

## Session State — 2026-04-09 (Session 2, post-midnight)

**Version:** `0.1.6` (`__version__` in `service/bot.py`)
**Branch:** `dev` at `a74fd42`
**Phase:** Phase D — Orchestration PoC BUILT, needs live channel test + ralph verification

### What Was Built This Session

#### Global Tool: `D:\IA\orchestration\` (also synced to `W:\Claude_Library\orchestration\`)

**MCP Channel Server** (`mcp-server/server.ts`):
- Same pattern as official Telegram plugin
- Watches agent mailbox file with chokidar
- Emits `notifications/claude/channel` to wake agents via SleepTool
- Provides tools: send, read_mailbox, write_approval, read_diff
- CC's all messages to monitor automatically
- Dependencies installed (bun), compiles and starts correctly

**Hook Scripts:**
- `check_gate.py` — PreToolUse blocks commit without dual approval, archives approvals
- `dispatch_next_bug.py` — PostToolUse marks done, injects next task, halts at batch boundaries
- `on_file_message.py` — FileChanged fallback handler
- `send.py` — Universal message router with monitor CC

**Agent Templates:** architect, critic, executor, playwright, monitor

**Launch:** tmux creator + MCP server registration per agent

#### Project Config: `.worktrees/v2-refactor-phase-d/gate/`
- `config.json` — 5 agents (architect, critic, ralph, playwright, monitor)
- `tasks.json` — 50 bugs with acceptance criteria (B1 set as current)
- `prompts/` — 5 rendered prompts with Phase D spec paths
- `mcp-config.json` — MCP server env per agent
- `hooks-ralph.json` — PreToolUse gate + PostToolUse dispatch
- Mailbox + approval + diff directories initialized

### Scripts Functionally Tested
- check_gate.py: deny without approvals ✅, pass non-commit ✅, allow with both approvals ✅, archive approvals ✅
- send.py: routes message ✅, CC's monitor ✅, Dubai timestamp ✅
- on_file_message.py: reads + returns additionalContext ✅, clears mailbox ✅
- dispatch_next_bug.py: marks done ✅, injects B2 with full protocol ✅
- MCP server: starts ✅, watches correct path ✅, shuts down cleanly ✅

### NOT YET TESTED (critical)
1. **Channel notification delivery** — does `notifications/claude/channel` actually wake a sleeping agent?
   - Telegram plugin wasn't delivering (likely 8 zombie bun processes fighting over token)
   - Kill zombies, test Telegram first, then test our MCP server
2. **Full end-to-end flow** — Ralph sends review → architect wakes → reviews → approves → Ralph commits
3. **Ralph verification via prd.json** — proper structured verification not done

### Architecture Decision: MCP Channel Server
- Separate terminal sessions per agent (not subagents)
- Communication via MCP `notifications/claude/channel` (same as Telegram plugin)
- SleepTool integration wakes agents within 1 second
- No sleep loops, no keyboard injection, no tmux send-keys
- Mechanical dispatch via Python hooks (no LLM orchestrator)
- File-based approval gate with audit trail archive

### Key Source Code References
- `channelNotification.ts` line 9: "SleepTool polls hasCommandsInQueue() and wakes within 1s"
- `channelNotification.ts` lines 925-947: `mcp.notification({ method: 'notifications/claude/channel', params: {...} })`
- Server declares `capabilities.experimental['claude/channel']` (line 359 of Telegram plugin)
- `execAgentHook.ts`: agent hooks CAN call SendMessage (not in disallowed tools list)

### Next Steps
1. Kill zombie bun processes, test Telegram channel delivery
2. Test our MCP server channel delivery in a live session
3. If channel works: full end-to-end test with 2 agents
4. If channel doesn't work: investigate feature gate, fallback to hybrid approach
5. Create prd.json for ralph verification of the orchestration system
6. Run the Phase D sprint
