# Dispatcher — Project State

**Version:** v0.1.11
**Branch:** dev
**Repo:** https://github.com/allanbell3d/dispatcher

---

## Current Phase

**Stabilization.** The 14-finding remediation pass is implemented in-repo. Bootstrap, hook installation, launcher/runtime alignment, and watcher/task progression now execute locally. Remaining work is proving the full gated sprint flow end-to-end with Allan on a real project.

## What Works (verified locally)

- Hook and script imports now resolve from the repo root.
- `install_hooks.py --all` writes and merges `.claude/settings.local.json`.
- FileChanged hooks cover both `.md` and `.json` inbox messages.
- Enforcement hooks fail secure on malformed payloads and trace allow/deny/skip/error paths.
- Watcher delivery only archives on actual delivery; deferred review requests stay pending.
- Task progression advances by canonical `task_id` and uses `.orchestrator/tasks/current_task.json`.
- Launcher dry-run works in `pwsh` and reads canonical runtime paths.
- `validate.py`, `doctor.py`, and the pytest suite all run successfully in this repo.

## What Doesn't Work (known)

1. **End-to-end sprint execution still needs Allan validation** — local tooling passes, but the full human-operated flow has not been confirmed on a live project.
2. **Legacy historical docs still exist** — frozen specs and fossil launcher references remain for history, even though the live contract is now documented separately.
3. **Windows PowerShell 5 is not a supported launcher shell** — `bin/orch_launcher.ps1` dry-run succeeds in `pwsh`; older `powershell.exe` lacks `ConvertFrom-Json -AsHashtable`.

## What Was Fixed In 0.1.11

| Priority | Fix | Scope |
|----------|-----|-------|
| 1 | Bootstrap repaired: `parents[0]` → `parents[1]` across entrypoints | hooks/ + scripts/ |
| 2 | Shared hook install now writes and reconciles `.claude/settings.local.json` | scripts/install_hooks.py |
| 3 | Halt flags and launcher wiring aligned to `.flag` files | `.orchestrator/halts/` + `bin/orch_launcher.ps1` |
| 4 | FileChanged hooks cover both `*.md` and `*.json` inbox traffic | scripts/install_hooks.py |
| 5 | Enforcement hooks fail secure on malformed input and trace every decision path | hooks/dispatch_gate.py, hooks/check_gate.py, hooks/inbox_access_guard.py |
| 6 | Watcher outbox retries preserve undelivered work instead of silently archiving it | scripts/watcher.py |
| 7 | Task progression now advances by canonical `task_id` and archives used merged verdicts | hooks/dispatch_next_bug.py |
| 8 | Current runtime contract documented in-repo | `docs_dev/CURRENT_CONTRACT.md` |

## Session Log

| Date | Who | What | Commit |
|------|-----|------|--------|
| 2026-04-10 | gate-architect | Initial gate orchestration system | `2635241` |
| 2026-04-11 | gate-architect | Engine scaffolding, watcher, hooks, lib | `669fdc8` |
| 2026-04-12 | gate-architect | Rename Orch/ → Orchestrator/ | `bbd8110` |
| 2026-04-13 | gate-architect | Waves 1-4, 5 critic cycles, launcher, specs, config migration | `5d3c724`→`c64428f` |
| 2026-04-13 | GPT | 14-finding code review (no local access, zip of files) | findings in docs_dev/reviews/gpt/ |
| 2026-04-13 | Codex | 3-pass review (architecture, code audit, launcher deep review) | findings in docs_dev/reviews/codex/ |
| 2026-04-13 | hookmaster | Live testing — confirmed bootstrap, identity, launcher failures | findings in docs_dev/reviews/ |
| 2026-04-13 | Allan | Extract dispatcher to standalone repo, push to GitHub | `73e49c1` on main |
| 2026-04-13 | Codex | Implemented full-finding stabilization pass: contract lock, hook hardening, watcher/task fixes, launcher/docs/test rebuild | pending commit |
