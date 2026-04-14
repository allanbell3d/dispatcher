# Dispatcher — Project State

**Version:** v0.1.13
**Branch:** dev
**Repo:** https://github.com/allanbell3d/dispatcher

---

## Documentation

- Approved guides and contracts live in `docs/`.
- Draft plans, reviews, reports, runbooks, and frozen working material live in `docs_dev/`.
- Promotion and naming rules are defined in `docs/DOCS_GOVERNANCE.md`.

---

## Current Phase

**Foundation consolidation complete.** The dispatcher now has governed approved docs, reusable install/test artifacts, refreshed coordinated role/init packs, and an explicit watcher-plan ingest contract. The next layer can start launcher/control-plane work on top of these foundations without reopening the documentation split.

## What Works (verified locally)

- Hook and script imports now resolve from the repo root.
- Approved entry-point docs now live in `docs/`, with promotion rules defined in `docs/DOCS_GOVERNANCE.md`.
- `install_hooks.py --all` writes and merges `.claude/settings.local.json`.
- FileChanged hook inventory now renders wildcard inbox matchers for both `.md` and `.json`.
- Enforcement hooks fail secure on malformed payloads and trace allow/deny/skip/error paths.
- Watcher delivery only archives on actual delivery; deferred review requests stay pending.
- Task progression advances by canonical `task_id` and uses `.orchestrator/tasks/current_task.json`.
- Launcher dry-run works in `pwsh`, reads canonical runtime paths, and exposes reviewer-set control.
- Reviewer activation is config-driven through `.orchestrator/config.json -> reviewers`.
- Codex reviewer profiles and memory overlays exist for `gate-codex-architect` and `gate-codex-critic`.
- `trace_hook()` honors configured Dubai time even when `ZoneInfo` is unavailable on Windows.
- Dispatcher artifact seeds, fixtures, and examples now exist in `artifacts/` and are exercised by smoke/tests.
- Watcher-plan normalization now has an explicit contract in `docs/PLAN_INGEST_CONTRACT.md`.
- Coordinated gate role prompts, memory overlays, and startup notes are aligned to the current dispatch contract.
- `validate.py`, `doctor.py`, and the pytest suite all run successfully in this repo.
- Idle projects now validate cleanly, and strict sprint preflight is exposed separately through `scripts/sprint_ready.py`, `scripts/orchestratorctl.py sprint-ready`, and the launcher.

## What Doesn't Work (known)

1. **End-to-end sprint execution still needs Allan validation** — local tooling passes, but the full human-operated flow has not been confirmed on a live project.
2. **Legacy historical docs still exist** — frozen specs and fossil launcher references remain for history, even though the live contract is now documented separately.
3. **Windows PowerShell 5 is not a supported launcher shell** — `bin/orch_launcher.ps1` dry-run succeeds in `pwsh`; older `powershell.exe` lacks `ConvertFrom-Json -AsHashtable`.
4. **Monitor/data-stream proof still needs a live sprint** — monitor ingest and fallback activity shipping are wired/documented, but Allan still needs to confirm the real mixed-agent flow under production use.

## What Was Fixed In 0.1.13

| Priority | Fix | Scope |
|----------|-----|-------|
| 1 | Approved docs were consolidated behind a formal governance split and new entry-point guides | `docs/INDEX.md`, `docs/DOCS_GOVERNANCE.md`, `docs/OPERATOR_GUIDE.md`, `docs/DEVELOPER_GUIDE.md` |
| 2 | Reusable install seeds, fixtures, and worked examples were added for dispatcher setup and tests | `artifacts/`, `tests/project_artifacts.py` |
| 3 | Dispatch contract smoke coverage now boots from repo artifacts and uses repo-local scratch paths | `scripts/dispatch_contract_smoke.py` |
| 4 | Watcher plan ingest is now governed by a written contract with stricter normalization validation | `docs/PLAN_INGEST_CONTRACT.md`, `scripts/normalize_plan.py`, `tests/test_plan_normalization.py` |
| 5 | Backlog items and writer prompts were normalized to the ingest contract, including structured `deps` support | `.orchestrator/tasks/tasks.json`, `agents/reference_prompts/dispatcher-plan-writer.md` |
| 6 | Coordinated role prompts were rebuilt around the current dispatch-first runtime contract | `agents/profiles/coordinated/`, `agents/protocols/coordinated/README.md` |
| 7 | Gate memory notes and startup protocols were simplified to current repo reality | `memory/gate-*/` |
| 8 | Draft role pack source material and execution inventories were staged under `docs_dev/` for future promotion | `docs_dev/roles/`, `docs_dev/reports/` |

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
| 2026-04-14 | Codex | Executed the dispatcher parallel plan pack across docs governance, artifact library, role/init refresh, and plan-ingest normalization; verified targeted pytest and dispatch smoke coverage | `daecd3c`→`06b18c6` |
