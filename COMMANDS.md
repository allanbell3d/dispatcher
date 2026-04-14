# CLI Commands

Start with `docs/OPERATOR_GUIDE.md` for the full operator flow. This file is the short command reference.

All commands run from the repo root. Python commands require the engine root on `sys.path`.

Primary launcher: `bin/orch_launcher.ps1`. The older `bin/launch.ps1` and `bin/launch.sh` scripts are legacy fossils.

---

## Pre-flight

```bash
# Check prerequisites (Python 3.10+, psmux/tmux, state dirs, hooks)
python scripts/doctor.py .

# Validate install/runtime health without requiring an active sprint
python scripts/validate.py .

# Fail unless a real sprint can start now (tasks loaded + current task selected)
python scripts/sprint_ready.py .

# Show all resolved paths from config
python scripts/orchestratorctl.py paths .
```

## Hook Management

```bash
# Install hooks for all agents (merges into settings.local.json, preserves existing hooks)
python scripts/install_hooks.py --all

# Install hooks for a single agent
python scripts/install_hooks.py --agent gate-ralph

# Disable a specific hook at runtime (creates flag file)
python scripts/orchestratorctl.py toggle-hook --hook <hook-name> --disable .

# Re-enable a hook
python scripts/orchestratorctl.py toggle-hook --hook <hook-name> --enable .
```

## Sprint Operations

```bash
# Show sprint status (current task, inbox depths, fan-ins, last activity)
python scripts/orchestratorctl.py status .

# Strict sprint preflight via the shared CLI wrapper
python scripts/orchestratorctl.py sprint-ready .

# Resume a stuck task (re-dispatch, optional --refan to re-notify reviewers)
python scripts/orchestratorctl.py resume . --agent gate-ralph [--refan]

# Emergency force-approve a stuck gate (audit logged)
python scripts/orchestratorctl.py override . --task TASK-123 --verdict approved --reason "operator override"
```

## Watcher

```bash
# Start watcher directly (use launcher for supervisor loop)
python scripts/watcher.py .

# Stop watcher cleanly
# Create the file: .orchestrator/runtime_flags/STOP
```

## Launcher (PowerShell 7 GUI)

```powershell
# Full control panel — sprint wizard, agent sessions, hook control, status, deploy
pwsh -NoProfile -File bin/orch_launcher.ps1
```

The launcher exposes separate `Validate Config` and `Sprint Ready Check` actions so idle-project health and active sprint preflight stay distinct.

Halt flags are `.flag` files in `.orchestrator/halts/`.

## Smoke Test

```bash
python scripts/dispatch_contract_smoke.py
```

Creates a temp project, runs message routing checks. Self-contained.

## Key Paths

All paths resolved from `.orchestrator/config.json` via `resolve_path()`:

| Key | Default |
|-----|---------|
| `state_root` | `.orchestrator` |
| `dispatch_root` | `dispatch` |
| `current_task` | `.orchestrator/tasks/current_task.json` |
| `trackers` | `.orchestrator/trackers.json` |
| `merged_verdicts` | `.orchestrator/merged_verdicts` |
| `halts` | `.orchestrator/halts` |
| `runtime_flags` | `.orchestrator/runtime_flags` |
| `logs` | `.orchestrator/logs` |
| `audit_log` | `.orchestrator/audit.log` |
