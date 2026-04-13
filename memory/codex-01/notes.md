# Codex-01 Notes

## Identity

- Repo: `D:\IA\dispatcher_repo`
- Agent folder: `memory/codex-01/`
- Primary persistent memory file for this agent: `memory/codex-01/notes.md`
- This folder is part of the repo and is intentionally committed.

## How This Memory Is Used

- Read `memory/AGENTS.md` first.
- Read `memory/codex-01/AGENTS.md` for role constraints.
- `notes.md` is the per-agent checkpoint and backup context file.
- Reading from the correct `memory/<agent>/...` path is part of the hook-based identity/permission model described in `memory/AGENTS.md`.

## Current Dispatcher Context

- Agent naming in dispatcher runtime is `gate-*`.
- Coordinated agent overlays belong under `memory/gate-*/`.
- Live dispatch traffic belongs under `dispatch/gate-*/`.
- Current runtime contract is documented in `docs_dev/CURRENT_CONTRACT.md`.

## Recent Codex Work In This Repo

- Implemented the dispatcher stabilization pass across bootstrap, hook installation, hook hardening, watcher/task progression, launcher alignment, docs, and tests.
- Corrected stale shared-memory references to the real repo memory model: `memory/...`.
- Removed the accidental empty placeholder folder that used the wrong name.

## Working Rules For This Agent

- Keep this file dispatcher-specific.
- Do not copy history from other repos into this memory file.
- Use this file for compact handoff notes, local repo context, and anything that should survive session compaction.
- If this agent is repurposed, update this file instead of creating a second shared-memory path.
