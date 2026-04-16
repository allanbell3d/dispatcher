# Changelog — Dispatcher Engine

All notable changes to the gated multi-agent sprint engine.
Extracted from the Advert repo commit history (2026-04-10 to 2026-04-13).

---

## Known Issues (as of 0.1.15)

Local blockers from the 14-finding review are addressed. Remaining risk is integration proof, not known broken core behavior:

| # | Issue | Severity |
|---|-------|----------|
| 1 | Full human-operated sprint flow still needs Allan confirmation on a real project | MEDIUM |
| 2 | Historical frozen docs still mention legacy paths and are intentionally preserved for audit context | LOW |
| 3 | `bin/orch_launcher.ps1` should be run with `pwsh`, not Windows PowerShell 5 | LOW |
| 4 | The mixed-agent idle handoff still needs Allan confirmation during a live Wave 5 sprint, even though the consolidated monitor pipeline now passes local integration coverage | MEDIUM |
| 5 | The new repo-run desktop control plane passes local smoke verification but still needs operator validation in real use | MEDIUM |

---

## [0.1.15] -- 2026-04-16 (launcher MVP stabilization + desktop control plane MVP)

### Added
- `desktop_app/` repo-run PySide6 desktop control plane MVP with dashboard, sprint controls, agent/session actions, task controls, hook controls, logs, reviewer presets, settings backup/restore, sprint mode, folder override, and deploy helpers.
- Launcher regression coverage for session naming, task dispatch, project targeting, deploy semantics, pause/stop behavior, quick-access paths, collection-count safety, and nav-state access.
- Repo dispatch-tree regression coverage to keep the checked-in sample state structurally valid and placeholder-only.

### Changed
- `bin/orch_launcher.ps1` now honors explicit project targeting for Python-backed actions, persists session-name mappings, handles existing session collisions during sprint launch, seeds first-task dispatch from selected plan data, uses safer deploy semantics, and surfaces better pause/stop status in the operator UI.
- `README.md`, `CLAUDE.md`, `QUICKSTART.md`, and `docs/OPERATOR_GUIDE.md` now describe the current repo-run launcher and desktop entry points instead of the old broken-state story.
- `.gitignore` now ignores the current repo-local pytest scratch directory patterns.

### Fixed
- Resolved launcher runtime crashes caused by hashtable nav-state property access and PowerShell scalar-vs-array `.Count` assumptions.
- Restored a clean checked-in sample state by removing stale halt flags and stray dispatch artifacts while preserving the validator-required placeholder directory structure.
- Aligned `tests/test_c3_install_hooks.py` with the current roles-based monitor-ingest contract.

---

## [0.1.14] -- 2026-04-14 (session-jsonl monitor pipeline)

### Added
- `docs/LOGGING_MONITOR_CONTRACT.md` as the concrete contract for the consolidated logging and monitor event pipeline.
- `scripts/monitor_tail.py`, `scripts/monitor_parse.py`, `scripts/monitor_render.py`, `scripts/monitor_route.py`, and `scripts/monitor_log.py` for checkpointed session tailing, canonical parsing, dual rendering, routing, and durable trace writing.
- Targeted monitor/logging coverage in `tests/test_monitor_tail.py`, `tests/test_monitor_parse.py`, `tests/test_monitor_render.py`, `tests/test_monitor_route.py`, `tests/test_monitor_log.py`, and `tests/test_monitor_integration.py`.

### Changed
- `hooks/monitor_ingest.py` now treats Claude session JSONL as the source of truth, tails incrementally with checkpoint tracking, renders trace and monitor output from the same parsed event flow, and writes durable trace rows to `.orchestrator/logs/monitor_trace.jsonl`.
- `scripts/install_hooks.py` now installs the consolidated monitor pipeline for coder and reviewer roles, while keeping `activity_logger.py` available as a legacy/manual path instead of the default live stream.
- Wave 5 monitor docs now reflect the tested behavior for session transcripts, monitor payloads, durable trace output, and reviewer-as-secondary routing.

### Fixed
- `scripts/monitor_render.py` now imports cleanly both as `scripts.monitor_render` and when executed directly in script-style contexts.

---

## [0.1.13] -- 2026-04-14 (dispatcher foundation pack)

### Added
- Approved documentation governance and entry-point guides in `docs/`, including `docs/INDEX.md`, `docs/DOCS_GOVERNANCE.md`, `docs/OPERATOR_GUIDE.md`, and `docs/DEVELOPER_GUIDE.md`.
- Reusable dispatcher artifact library under `artifacts/` for install seeds, fixtures, and operator-facing examples.
- `docs/PLAN_INGEST_CONTRACT.md` as the canonical watcher-ingestible JSON contract.
- Draft role-pack contract, role drafts, and execution inventories under `docs_dev/`.
- Focused regression coverage for plan normalization plus reusable test artifact helpers in `tests/project_artifacts.py`.

### Changed
- `scripts/dispatch_contract_smoke.py` now boots from checked-in artifacts and uses repo-local scratch space for safer smoke runs.
- `scripts/normalize_plan.py` now validates placeholders and optional fields more strictly, including explicit support for `deps`.
- `.orchestrator/tasks/tasks.json` and `agents/reference_prompts/dispatcher-plan-writer.md` now align with the documented ingest contract.
- Coordinated role prompts, memory overlays, and startup notes were rebuilt around the current dispatch-first runtime contract.
- Top-level operator docs now consistently preserve the `docs/` approved versus `docs_dev/` draft split.

---

## [0.1.12] — 2026-04-14 (role activation + wave 5 prep)

### Added
- Codex coordinated reviewer profiles for `gate-codex-architect` and `gate-codex-critic`, with matching `memory/` overlays and seeded dispatch folders.
- `reviewers` config block with `available`, `active`, and `presets`, plus CLI controls via `scripts/orchestratorctl.py reviewers ...`.
- Launcher reviewer-set control entry in `bin/orch_launcher.ps1`.
- Wave 5 operator pack under `docs_dev/wave5/`.
- `scripts/normalize_plan.py`, watcher plan format guide, and repo-local dispatcher plan-writer prompt/spec.
- Backlog enrichment notes and role draft docs under `docs_dev/`.

### Changed
- Hook install inventory now emits wildcard `dispatch/*/inbox/*.md` and `dispatch/*/inbox/*.json` FileChanged matchers.
- `trace_hook()` now honors configured Dubai time via a Windows-safe timezone fallback when `ZoneInfo` data is unavailable.
- Dubizzle task backlog text was cleaned up for mojibake and duplicate shorthand acceptance criteria.
- Coordinated protocol docs now point to `dispatch/gate-<name>/inbox/` and active reviewer routing.
- Validation now treats taskless projects as healthy-but-idle, while `scripts/sprint_ready.py` and launcher `Sprint Ready Check` provide a strict active-sprint preflight.

---

## [0.1.11] — 2026-04-13 (stabilization pass)

### Fixed
- Repair repo-root bootstrap across hooks and scripts so `lib.common` imports work from direct entrypoint execution.
- Unify current runtime contract around `gate-*` identity, `.orchestrator/tasks/current_task.json`, canonical decision trace path, and checked-in state aligned to that contract.
- Make `install_hooks.py --all` write and reconcile shared `.claude/settings.local.json`, keyed by event + matcher + command, with both `.md` and `.json` inbox triggers.
- Harden enforcement hooks to fail secure on malformed payloads and emit decision traces for early-return, skip, allow, deny, and error paths.
- Prevent inbox message loss by moving inbox files only after successful hook output emission.
- Reduce telemetry leakage by expanding token redaction and switching activity logging to metadata-first summaries.
- Keep watcher outbox items pending when nothing was delivered, and delay fan-in creation until at least one reviewer actually received the request.
- Advance tasks by canonical `task_id`, archive used merged verdicts, and stop guessing resume task identity from the agent name.
- Align launcher runtime paths, halt/resume wiring, hook inventory, and session naming with the live contract.
- Replace dead script-style installer/bootstrap tests with runnable pytest coverage and add focused regression coverage for bootstrap, install-hooks, watcher retry, and task progression.

### Added
- `docs_dev/CURRENT_CONTRACT.md` documenting the live repo contract and intentional divergence from frozen historical specs.
- Repo placeholders for canonical gate inboxes, halt flags, `memory/`, and `.orchestrator/last_tool_use/`.

### Changed
- Project state files and top-level operator docs now describe the live dispatcher layout instead of the pre-extract `orchestrator/` subtree.

---

## [0.1.10] — 2026-04-13 (14:29–19:01)

### Added
- Launcher complete rebuild from spec — all 38 menu items, install submenu, sprint wizard, mma-launcher patterns (`7a80a63`)
- Launcher spec updates — install options submenu, project selection, deploy/delete specs (`f0466bf`)

### Fixed
- Launcher: checkbox toggle, supervisor kill, Unicode dividers, atomic writes, InitialPos, wizard prompts (`5f75fec`)
- Migrate config to schema-aligned keys, gate-prefixed names everywhere (`c64428f`)

### Documented
- GPT review findings (14 issues) + hookmaster live test results saved (`7e0c5d8`)

---

## [0.1.9] — 2026-04-13 (12:39–13:16)

### Changed
- **Identity model decision:** gate-prefixed names everywhere — `gate-ralph`, `gate-architect`, `gate-critic`, `gate-monitor`, `gate-playwright`. No stripping, no building. (`fe2c0e2`, `5cd5936`, `3729240`)
- **Flatten structure:** `dispatcher/orchestrator/` contents moved up to `dispatcher/`, install creates project dirs (`a542bb5`)

---

## [0.1.8] — 2026-04-13 (11:45–12:25)

### Added
- Launcher UX rewrite — flicker-free rendering, mma-launcher patterns, PID fix, atomic writes, pause/halt (`72ca3f6`)
- Sprint profiles — sprint_on.json + sprint_off.json for roles.json patching (`b79c4ef`)
- Wizard Steps 2-3 — per-agent launch mode + session name editing (`1b920fe`)
- Backup/restore — roles.json + settings files before patching, restore menu, keep last 5 (`bfe3f35`)
- Folder picker dialog for project selection, change-project menu item (`59a6a02`)

### Changed
- Migrate all `resolve_paths()` callers to `resolve_path()`, delete deprecated ResolvedPaths dataclass (`fcadeee`)

### Fixed
- Full review remediation — inbox_access_guard exit 2, check_gate shlex, is_hook_disabled all hooks, hookSpecificOutput wrapper, atomic writes, hardcoded allan cleanup, config paths (`321e784`)

---

## [0.1.7] — 2026-04-13 (09:12–10:25)

### Added — Wave 4
- Launcher core framework + status dashboard (`2fcb474`)
- `trace_hook()` decision trace logger in lib/common.py — Component 22 (`be83e09`)
- Wire trace_hook into all 8 hooks (`34d9a3e`)
- Hook runtime toggle via flag files + CLI (`4ddba36`)
- Liveness ticker thread in watcher.py (`9b32b4d`)
- orchestratorctl commands: status (`223df49`), resume (`2324f22`), override (`dd53f61`)
- install-hooks CLI wrapper in orchestratorctl (`1e23a34`)
- Doctor extensions — trace, hooks, profiles health checks (`00fd124`)
- Path resolution test harness (`b6b1eed`)
- Pre-flight dirs and sprint_profiles stub (`c0ce38`)
- Liveness spec, dual-write logging spec, Wave 4 plan updates (`36c362a`)

### Fixed — Wave 4 reviews
- B review — rename inbox_depth to inbox_count, log wake failures (`3ee3246`)
- C review — add `--refan` to resume, fix override schema (override+by), tighten test (`0f7a11a`)
- D review — NAS dual-write, session-ID filename, command truncation, agent var, dup import (`a0c6ad5`)
- A review — GATE_AGENT_NAME, wizard, sprint mode roles.json, menu items, supervisor, PID detection (`7891f9c`)

---

## [0.1.6] — 2026-04-13 (07:57–08:00)

### Fixed
- Wave 3 post-review — guard escalation_target, dup import, D2 comment, poll-based D2 test, stdin tests (`a8ed18e`)
- spec v2.4 finalized, Wave 3 marked complete, launch scripts added, verdict schema fix (`5574e77`)

---

## [0.1.5] — 2026-04-13 (06:30–07:15)

### Added — Wave 3
- DELIVERED state in dispatch_gate — tracker-based, git-commit-only until verdict arrives (`5dfdbe4`)
- check_gate rewrite — reads merged_verdicts, checks protected_branches, drops legacy approvals_dir (`07a3fa0`)
- MERGE fan-in — watcher writes merged_verdicts JSON on unanimous consensus, guarded trackers.pop (`d7fc41a`)
- Crash reporting — watcher catches unhandled exceptions, writes traceback to audit_log, notifies cc_all (`b7622e0`)
- install_hooks: wire dispatch_gate for all agents, `--all` flag, executor-only monitor_ingest+check_gate (`925a177`)
- tests/ directory created for Wave 3 component tests (`adec768`)

### Fixed
- guard resolve_path in DELIVERED block, tighten git commit check with shlex (`93afae0`)
- explicit return after _deny in check_gate, guard detached HEAD, fix branch test (`d5aa92`)
- move if-condition to outer hook entry (schema fix for install_hooks), add if-placement test (`6635cf4`)
- guard zero-reviewer unanimous edge case, align vote-counting to tracker.required (`5b033a7`)
- guard crash-handler log(), tighten audit assertion to require watcher_crash event (`80d1bae`)
- replace Unicode arrows with ASCII for Windows cp1252 compat (`081cc20`)

---

## [0.1.4] — 2026-04-13 (05:30–06:00)

### Added — Wave 2
- dispatch_gate enforcement hook — tool-level gating on protected branches (`e8c63ba`)
- Halt helpers — `set_halt()`, `clear_halt()`, `is_halted()` in lib/common.py (`e8c63ba`)
- audit_log() — append-only audit trail for all engine decisions (`e8c63ba`)
- Schema validator — config.json validated against config_schema.json (`e8c63ba`)
- COPY fan-out — review requests delivered to all configured reviewers (`e8c63ba`)
- Plan validator — plan JSON validated against plan_schema.json (`e8c63ba`)

---

## [0.1.3] — 2026-04-13 (early morning)

### Added
- Consolidate dispatcher structure — specs, reviews, remediation plans into `dispatcher/` (`5d3c724`)

### Fixed
- Wave 1 remediation R3 — P3 guards on every hook, P4 fail-secure wrappers, hardcoded name cleanup, schema alignment (`29ad51e`)
- Rename spec to MASTER_SPECS_MERGED, R4 remediation, ref doc cleanup (`59f2ee1`)

---

## [0.1.2] — 2026-04-12

### Changed
- Rename Orch/ to Orchestrator/ — canonical folder name established (`bbd8110`)

---

## [0.1.1] — 2026-04-11

### Added
- Orch/ orchestration engine — watcher, hooks, lib/common.py, gate infrastructure refresh (`669fdc8`)

---

## [0.1.0] — 2026-04-10

### Added
- Initial gate orchestration system — file-based dispatch model, agent memory folders, early hook scaffolding (`2635241`)
