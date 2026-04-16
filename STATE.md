# Dispatcher — Project State

**Version:** v0.1.15
**Branch:** dev
**Repo:** https://github.com/allanbell3d/dispatcher

---

## Documentation

- Approved guides and contracts live in `docs/`.
- Draft plans, reviews, reports, runbooks, and frozen working material live in `docs_dev/`.
- Promotion and naming rules are defined in `docs/DOCS_GOVERNANCE.md`.

---

## Current Phase

**Foundation consolidation plus monitor/logging pipeline complete.** The dispatcher now has governed approved docs, reusable install/test artifacts, refreshed coordinated role/init packs, an explicit watcher-plan ingest contract, and a consolidated session-JSONL monitor/logging pipeline. The next layer can focus on live sprint proof and launcher/control-plane work without reopening the logging/monitor contract.

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
- Claude session JSONL is now the source of truth for the live monitor/logging ingest path.
- `monitor_ingest.py` tails transcripts incrementally with session-keyed byte-offset checkpoints and safe partial-line handling.
- One parsed event flow now produces both durable trace output and a monitor-safe render from the same underlying session data.
- Monitor routing treats `gate-ralph` as the primary live source and reviewer sessions as secondary inputs when Ralph is idle.
- Durable monitor trace rows append to `.orchestrator/logs/monitor_trace.jsonl`, while rendered monitor payloads land in `dispatch/gate-monitor/inbox/`.
- Coordinated gate role prompts, memory overlays, and startup notes are aligned to the current dispatch contract.
- `validate.py`, `doctor.py`, and the pytest suite all run successfully in this repo.
- Idle projects now validate cleanly, and strict sprint preflight is exposed separately through `scripts/sprint_ready.py`, `scripts/orchestratorctl.py sprint-ready`, and the launcher.
- The PowerShell launcher now supports stricter project targeting, safer deploy semantics, sprint launch task seeding, session-name persistence, better pause/stop status reporting, and a cleaner checked-in sample state.
- A repo-run PySide6 desktop control plane now exists under `desktop_app/` and constructs successfully in local smoke verification.

## What Doesn't Work (known)

1. **End-to-end sprint execution still needs Allan validation** — local tooling passes, but the full human-operated flow has not been confirmed on a live project.
2. **Legacy historical docs still exist** — frozen specs and fossil launcher references remain for history, even though the live contract is now documented separately.
3. **Windows PowerShell 5 is not a supported launcher shell** — `bin/orch_launcher.ps1` dry-run succeeds in `pwsh`; older `powershell.exe` lacks `ConvertFrom-Json -AsHashtable`.
4. **Mixed-agent live monitor proof still needs a live sprint** — the consolidated JSONL pipeline is covered locally, but Allan still needs to confirm the real reviewer-idle handoff flow under production use.
5. **Desktop app still needs real operator validation** — local smoke verification passes, but the PySide6 surface still needs real-world use feedback.

## What Was Fixed In 0.1.14

| Priority | Fix | Scope |
|----------|-----|-------|
| 1 | Live monitor/logging ingest now tails Claude session JSONL instead of relying on hook payload summaries | `hooks/monitor_ingest.py`, `scripts/monitor_tail.py` |
| 2 | Canonical parsing now preserves full session content and drives both durable trace and monitor-safe renders from one event flow | `scripts/monitor_parse.py`, `scripts/monitor_render.py` |
| 3 | Durable trace logging and primary/secondary monitor routing are now explicit runtime components | `scripts/monitor_log.py`, `scripts/monitor_route.py` |
| 4 | Default hook installation now wires the consolidated monitor pipeline for coder and reviewer roles | `scripts/install_hooks.py` |
| 5 | Monitor/logging docs now describe the tested runtime truth, including checkpoints, trace output, and reviewer idle handoff behavior | `docs/LOGGING_MONITOR_CONTRACT.md`, `docs_dev/wave5/LOGGING_AND_DATA_STREAMS.md`, `docs_dev/wave5/MONITOR_AGENT_SETUP.md` |
| 6 | Targeted regression coverage now proves the JSONL tailer, parser, renderers, router, durable trace writer, and dispatcher monitor integration | `tests/test_monitor_tail.py`, `tests/test_monitor_parse.py`, `tests/test_monitor_render.py`, `tests/test_monitor_route.py`, `tests/test_monitor_log.py`, `tests/test_monitor_integration.py`, `tests/test_monitor_stream.py` |

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
| 2026-04-14 | Codex | Consolidated dispatcher logging + monitor streaming around session JSONL tailing, canonical parse/render flow, durable trace logging, reviewer-secondary routing, and tested Wave 5 docs | `0a5da58`→`b1d015b` |
| 2026-04-16 | Codex | Stabilized the launcher MVP, restored a clean sample dispatch state, added launcher regressions, built a repo-run PySide6 desktop control plane MVP, and verified local pytest/validate/sprint-ready/desktop smoke | `e371d5b` |
