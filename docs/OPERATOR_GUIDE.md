# Dispatcher Operator Guide

## What Dispatcher Is

Dispatcher is the engine repo for Allan's gated sprint workflow. This repo provides the launcher, watcher, hooks, profiles, and reference config. A target project gets deployed copies of `.orchestrator/` and `dispatch/`, while the engine code continues to live here.

If you are trying to run or troubleshoot a sprint, start here first.

## First Reads

- [`INDEX.md`](INDEX.md) for the approved docs map
- [`../COMMANDS.md`](../COMMANDS.md) for CLI commands
- [`../QUICKSTART.md`](../QUICKSTART.md) for deploy/setup steps
- [`../SMOKE_TEST.md`](../SMOKE_TEST.md) for manual verification

Wave-specific trial material and live-sprint runbooks remain in `docs_dev/wave5/`.

Reusable sample artifacts now live under `artifacts/`:

- `artifacts/install/` for bootstrap seeds
- `artifacts/examples/` for readable examples
- `artifacts/fixtures/` for test and smoke inputs

## Health Checks Vs Sprint Readiness

Dispatcher uses three different checks on purpose:

1. `python scripts/doctor.py <project>`
   Checks prerequisites such as Python, PowerShell/tmux/psmux, and required repo/project structure.
2. `python scripts/validate.py <project>`
   Checks install/runtime health without requiring an active sprint.
3. `python scripts/sprint_ready.py <project>`
   Fails unless a real sprint can start now: tasks loaded, current task selected, and runtime paths consistent.

Use `validate.py` after install or config edits. Use `sprint_ready.py` only when you are about to run a real sprint.

## Launcher Entry Point

Primary entry point:

```powershell
pwsh -NoProfile -File bin/orch_launcher.ps1
```

The launcher is the operator control panel for:

- deploy/install actions
- config validation
- sprint-ready checks
- watcher start/stop
- agent session launch
- status views
- runtime hook toggles

`bin/launch.ps1` and `bin/launch.sh` are legacy fossils, not the preferred operator path.

## Typical Operator Flow

1. Deploy `.orchestrator/` and `dispatch/` to the target project.
2. Edit `<project>/.orchestrator/config.json`.
3. Install hooks with `python scripts/install_hooks.py --all --project <project>`.
4. Run `doctor.py` and `validate.py`.
5. Load a watcher-ingestible plan and a task backlog.
6. Set `.orchestrator/tasks/current_task.json`.
7. Run `sprint_ready.py`.
8. Launch the watcher and selected agent sessions from the launcher.

## Watcher Basics

The watcher is the file-based router/supervisor loop. In normal operation it:

- reads agent outboxes
- fans review requests out to configured reviewers
- merges reviewer verdicts
- writes merged verdict state
- advances or re-dispatches the current task flow
- keeps the dispatch folders moving without agents reading the full plan directly

The main direct operator command is:

```bash
python scripts/watcher.py <project>
```

In most cases, use the launcher instead of starting the watcher manually.

## Task And Plan Basics

Dispatcher separates plan, backlog, and active-task state:

- plan files live under `.orchestrator/plans/`
- backlog tasks live in `.orchestrator/tasks/tasks.json`
- the active task pointer lives in `.orchestrator/tasks/current_task.json`
- merged review verdicts live in `.orchestrator/merged_verdicts/`

Agents do not treat `.orchestrator/` as a mailbox. Live traffic moves through `dispatch/<agent>/`.

## Logs And Evidence

Primary runtime evidence lives under the target project's `.orchestrator/` tree:

- `.orchestrator/logs/decision_trace.log`
- `.orchestrator/audit.log`
- `.orchestrator/trackers.json`
- `.orchestrator/merged_verdicts/`

Repo-side working evidence and review artifacts live under:

- `docs_dev/reviews/`
- `docs_dev/reports/`
- `docs_dev/test_results/`
- `docs_dev/wave5/`

## Where To Read Next

- Use [`../COMMANDS.md`](../COMMANDS.md) when you already know the workflow and just need exact commands.
- Use [`../QUICKSTART.md`](../QUICKSTART.md) when deploying dispatcher into a fresh project.
- Use [`../SMOKE_TEST.md`](../SMOKE_TEST.md) when proving the flow or diagnosing setup drift.
- Use `docs_dev/wave5/` when running or analyzing the current live-sprint rehearsal pack.
- Use `artifacts/examples/` when you need a current sample task, plan, or message shape.
