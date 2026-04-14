# Dispatcher — Project State

**Version:** v0.1.12
**Branch:** dev
**Repo:** https://github.com/allanbell3d/dispatcher

---

## Documentation

- Approved guides and contracts live in `docs/`.
- Draft plans, reviews, reports, runbooks, and frozen working material live in `docs_dev/`.
- Promotion and naming rules are defined in `docs/DOCS_GOVERNANCE.md`.

---

## Current Phase

**Stabilization.** The 14-finding remediation pass is implemented in-repo, and the next control layer is now landing: reviewer activation, Codex reviewer profiles, wildcard hook install reduction, Wave 5 operator docs, and plan-ingest tooling. Remaining work is proving the full gated sprint flow end-to-end with Allan on a real project.

## What Works (verified locally)

- Hook and script imports now resolve from the repo root.
- `install_hooks.py --all` writes and merges `.claude/settings.local.json`.
- FileChanged hook inventory now renders wildcard inbox matchers for both `.md` and `.json`.
- Enforcement hooks fail secure on malformed payloads and trace allow/deny/skip/error paths.
- Watcher delivery only archives on actual delivery; deferred review requests stay pending.
- Task progression advances by canonical `task_id` and uses `.orchestrator/tasks/current_task.json`.
- Launcher dry-run works in `pwsh`, reads canonical runtime paths, and exposes reviewer-set control.
- Reviewer activation is config-driven through `.orchestrator/config.json -> reviewers`.
- Codex reviewer profiles and memory overlays exist for `gate-codex-architect` and `gate-codex-critic`.
- `trace_hook()` honors configured Dubai time even when `ZoneInfo` is unavailable on Windows.
- Wave 5 operator docs and watcher-plan normalization tooling are present in-repo.
- `validate.py`, `doctor.py`, and the pytest suite all run successfully in this repo.
- Idle projects now validate cleanly, and strict sprint preflight is exposed separately through `scripts/sprint_ready.py`, `scripts/orchestratorctl.py sprint-ready`, and the launcher.

## What Doesn't Work (known)

1. **End-to-end sprint execution still needs Allan validation** — local tooling passes, but the full human-operated flow has not been confirmed on a live project.
2. **Legacy historical docs still exist** — frozen specs and fossil launcher references remain for history, even though the live contract is now documented separately.
3. **Windows PowerShell 5 is not a supported launcher shell** — `bin/orch_launcher.ps1` dry-run succeeds in `pwsh`; older `powershell.exe` lacks `ConvertFrom-Json -AsHashtable`.
4. **Monitor/data-stream proof still needs a live sprint** — monitor ingest and fallback activity shipping are wired/documented, but Allan still needs to confirm the real mixed-agent flow under production use.

## What Was Fixed In 0.1.12

| Priority | Fix | Scope |
|----------|-----|-------|
| 1 | Reviewer activation moved to a dedicated `reviewers` config block with presets and CLI control | `.orchestrator/config.json`, `schemas/config_schema.json`, `scripts/orchestratorctl.py` |
| 2 | Codex reviewer profiles, memory overlays, and dispatch folders added | `agents/profiles/coordinated/`, `memory/`, `dispatch/` |
| 3 | FileChanged install inventory reduced to wildcard inbox matchers | `scripts/install_hooks.py` |
| 4 | Launcher now exposes reviewer-set control in dry-run verified menu flow | `bin/orch_launcher.ps1` |
| 5 | Trace timestamps respect configured Dubai time with Windows-safe fallback | `lib/common.py` |
| 6 | Dubizzle task backlog cleaned up for mojibake and duplicate shorthand acceptance criteria | `.orchestrator/tasks/tasks.json` |
| 7 | Plan normalizer and watcher plan format guidance added | `scripts/normalize_plan.py`, `docs_dev/plans/WATCHER_PLAN_FORMAT_GUIDE.md` |
| 8 | Wave 5 operator doc pack added | `docs_dev/wave5/` |

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
| 2026-04-14 | Codex | Added reviewer activation presets/CLI, Codex reviewer profiles, wildcard hook install, launcher reviewer menu, Wave 5 docs, plan normalizer, and Dubizzle backlog cleanup | pending commit |
| 2026-04-14 | Codex | Split install validation from sprint preflight with `sprint_ready.py`, launcher action, and operator doc updates | pending commit |
