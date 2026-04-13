# Quick Start

## 1. Prerequisites

- Python 3.10+
- psmux (Windows) or tmux (Linux/Mac)
- Claude Code CLI

## 2. Project structure

Your project needs:
```
<project>/
├── .orchestrator/config.json    ← project config (team, routing, gates, paths)
├── dispatch/                    ← created by launcher or manually
└── (your project code)
```

Engine code lives separately at:
- `W:\Claude_Library\orchestrator\` (NAS primary)
- `D:\IA\orchestrator\` (fallback)

Agent profiles at:
- `W:\Claude_Library\agents\` (NAS primary)
- `D:\IA\agents\` (fallback)

## 3. Validate

```powershell
python orchestrator/scripts/orchestratorctl.py doctor
python orchestrator/scripts/orchestratorctl.py validate
```

Both must pass. Doctor checks prereqs. Validate checks config schema + cross-references.

## 4. Install hooks

```powershell
python orchestrator/scripts/orchestratorctl.py install-hooks --all
```

Merges orchestrator hooks into `settings.local.json`. Does NOT overwrite Allan's existing hooks.

## 5. Launch

```powershell
powershell -File orchestrator/bin/orch_launcher.ps1
```

The launcher:
1. Validates config
2. Creates dispatch folders
3. Starts watcher (with supervisor restart loop)
4. Opens psmux terminals per agent with `GATE_AGENT_NAME` set
5. Optionally launches Claude in each terminal
6. Dispatches first task from plan

## 6. During a sprint

- Coder works on a task → monitor watches live → coder delivers → reviewers gate the commit
- `orch status` shows progress
- `orch override <task_id>` for emergency gate bypass
- `orch resume <task_id>` for stuck tasks
- Pause: launcher menu or write halt flags
- Stop: write `.orchestrator/runtime_flags/STOP`

## 7. Logs

Dual-write:
- **NAS archive:** `W:\Claude_Library\orchestrator\logs\<project>\`
- **Project local:** `.orchestrator/logs/`

Key files:
- `decision_trace_<session>.log` — every hook call with agent, tool, decision, reason, timing
- `audit.log` — state changes, fan-in events, overrides
- `watcher.log` — watcher lifecycle
