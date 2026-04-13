# CLI Commands

All commands via `orchestratorctl.py` or `.orchestrator/bin/orch.ps1`.

## Pre-flight

```powershell
# Resolve and display all config paths
python orchestrator/scripts/orchestratorctl.py paths

# Check prerequisites (Python 3.10+, psmux/tmux, state_root, hooks)
python orchestrator/scripts/orchestratorctl.py doctor

# Validate config against schema + cross-reference agent names
python orchestrator/scripts/orchestratorctl.py validate
```

## Hook management

```powershell
# Install hooks for all agents (merges into settings.local.json, preserves existing hooks)
python orchestrator/scripts/orchestratorctl.py install-hooks --all

# Disable a specific hook (sets if condition to never-match)
python orchestrator/scripts/orchestratorctl.py disable <hook-name>

# Re-enable a hook
python orchestrator/scripts/orchestratorctl.py enable <hook-name>
```

## Sprint operations

```powershell
# Show sprint status (current task, inbox depths, fan-ins, last activity)
python orchestrator/scripts/orchestratorctl.py status

# Resume a stuck task (re-dispatch, optional --refan to re-notify reviewers)
python orchestrator/scripts/orchestratorctl.py resume <task_id> [--refan]

# Emergency force-approve a stuck gate (audit logged)
python orchestrator/scripts/orchestratorctl.py override <task_id>
```

## Watcher

```powershell
# Start watcher directly (use launcher for supervisor loop)
python orchestrator/scripts/watcher.py

# Stop watcher cleanly
New-Item .orchestrator/runtime_flags/STOP -ItemType File
```

## Launcher (Wave 4)

```powershell
# Full GUI control panel — sprint wizard, agent sessions, hook control, status
powershell -File orchestrator/bin/orch_launcher.ps1
```

## Smoke test

```powershell
python orchestrator/scripts/dispatch_contract_smoke.py
```

## Notes

- MCP commands removed (frozen per spec rule #20)
- All paths resolved from `.orchestrator/config.json` — commands work from any project with a valid config
