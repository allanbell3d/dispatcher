# CLI Commands

All commands run from the repo root. Python commands require the engine root on `sys.path`.

**Note:** As of v0.1.10, all Python commands fail with `ModuleNotFoundError` due to the bootstrap issue. Fix `parents[0]` → `parents[1]` in all hooks/ and scripts/ first, or set `PYTHONPATH` to the repo root.

Primary launcher: `bin/orch_launcher.ps1`. The older `bin/launch.ps1` and `bin/launch.sh` scripts are legacy fossils.

---

## Pre-flight

```bash
# Check prerequisites (Python 3.10+, psmux/tmux, state dirs, hooks)
python scripts/doctor.py .

# Validate config against schema + cross-reference agent names
python scripts/validate.py .

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
python scripts/orchestratorctl.py disable <hook-name> .

# Re-enable a hook
python scripts/orchestratorctl.py enable <hook-name> .
```

## Sprint Operations

```bash
# Show sprint status (current task, inbox depths, fan-ins, last activity)
python scripts/orchestratorctl.py status .

# Resume a stuck task (re-dispatch, optional --refan to re-notify reviewers)
python scripts/orchestratorctl.py resume <task_id> . [--refan]

# Emergency force-approve a stuck gate (audit logged)
python scripts/orchestratorctl.py override <task_id> .
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
powershell -File bin/orch_launcher.ps1
```

38 menu items: launch/pause/resume/stop sprint, status dashboard, agent terminals, hook toggles, deploy to project, backup/restore, and more. See `docs_dev/specs_frozen/LAUNCHER_SPEC.md` for the full spec.

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
