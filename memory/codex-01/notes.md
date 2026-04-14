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

## Session 2026-04-14

### Validate vs Sprint-Ready Split

- Added `scripts/sprint_ready.py` as strict active-sprint preflight.
- Kept `scripts/validate.py` as install/runtime health validation, with idle projects treated as warning-only.
- Wired `sprint-ready` into `scripts/orchestratorctl.py` and added launcher menu item `Sprint Ready Check`.
- Updated operator docs and wrote decision note:
  - `docs_dev/plans/executed/2026-04-14_validate-vs-sprint-ready_decision-note.md`
  - `docs_dev/wave5/WAVE5_GO_NO_GO.md`
  - `docs_dev/wave5/WAVE5_EXECUTION_RUNBOOK.md`
  - `COMMANDS.md`
  - `QUICKSTART.md`
  - `SMOKE_TEST.md`

### Verified Today

- `python -m pytest tests/test_validate_idle_project.py tests/test_sprint_ready.py tests/test_launcher_sprint_ready_menu.py -q` passed.
- `python scripts/validate.py D:\IA\dubizzle` passes with idle warning.
- `python scripts/sprint_ready.py D:\IA\dubizzle` fails correctly when no tasks are loaded.
- `python scripts/sprint_ready.py .` and `python scripts/orchestratorctl.py sprint-ready .` pass in repo.
- `pwsh -NoProfile -File bin/orch_launcher.ps1 -DryRun` passes.

### Live Dubizzle Hook Test Findings

- Took over `psmux` sessions `gate-ralph` and `gate-critic`.
- Set `GATE_AGENT_NAME` in both panes and launched Claude in `D:\IA\dubizzle`.
- Confirmed two identity layers are in play:
  - Allan hooks use session role stamping from memory reads / hook state.
  - Orchestrator hooks use `GATE_AGENT_NAME`.
- Main live blocker was hook command path format in `D:\IA\dubizzle\.claude\settings.local.json`.
- UNC/NAS hook commands were causing bad execution behavior inside live Claude hook handling.
- User confirmed project hook JSON changes load live in this environment.

### Hook Path Fix Applied

- Fixed `scripts/install_hooks.py` so hook commands render from configured `shared_roots.orchestrator_primary`, not the local installer execution path.
- Added regression coverage in `tests/test_c3_install_hooks.py`.
- Reinstalled hooks for `D:\IA\dubizzle`.
- Confirmed installed project hooks now use:
  - `python "W:\Claude_Library\orchestrator\hooks\dispatch_gate.py"`
  - `python "W:\Claude_Library\orchestrator\hooks\inbox_access_guard.py"`
  - `python "W:\Claude_Library\orchestrator\hooks\check_gate.py"`
  - `python "W:\Claude_Library\orchestrator\hooks\activity_logger.py"`
  - `python "W:\Claude_Library\orchestrator\hooks\monitor_ingest.py"`
  - `python "W:\Claude_Library\orchestrator\hooks\dispatch_next_bug.py"`
  - `python "W:\Claude_Library\orchestrator\hooks\on_file_message.py"`
  - `python "W:\Claude_Library\orchestrator\hooks\stop_notify.py"`

### Important Context For Tomorrow

- User says `settings.local.json` changes are live in their setup; defer to that observed behavior.
- There is also a pending global-hook improvement request outside the repo:
  - Allan hook role detection should use `GATE_AGENT_NAME` as primary source before memory-read fallback.
  - Relevant global files inspected:
    - `C:\Users\Allan\.claude\hooks\pre-tool-guard.ps1`
    - `C:\Users\Allan\.claude\hooks\post-tool-handler.ps1`
    - `C:\Users\Allan\.claude\hooks\roles.json`
- This global hook bridge was not implemented in this repo session.

### Next Best Step

- Resume live Dubizzle testing with the corrected `W:\...` project hook commands.
- Re-test:
  - minimal Claude tool use in `gate-ralph` / `gate-critic`
  - `decision_trace.log`
  - `audit.log`
  - monitor inbox traffic in `dispatch/gate-monitor/inbox/`
- If role blocking persists, patch Allan global hook role stamping to honor `GATE_AGENT_NAME` first.
