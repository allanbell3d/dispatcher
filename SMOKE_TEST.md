# Smoke Test Guide

## Quick smoke (automated)

```powershell
python orchestrator/scripts/dispatch_contract_smoke.py
```

Creates a temp project, runs the watcher for a few seconds, verifies message routing. Self-contained — no external deps.

## Manual smoke — full gate lifecycle

### 1. Pre-flight
```powershell
python orchestrator/scripts/orchestratorctl.py doctor
python orchestrator/scripts/orchestratorctl.py validate
```

### 2. Install hooks
```powershell
python orchestrator/scripts/orchestratorctl.py install-hooks --all
```

### 3. Launch
```powershell
powershell -File orchestrator/bin/orch_launcher.ps1
```
Select 2+ agents. Verify status dashboard shows agents as ready.

### 4. Dispatch a task
Drop a task JSON in `.orchestrator/tasks/`:
```json
{"task_id": "SMOKE-1", "title": "Test task", "acceptance_criteria": ["Passes"], "reference_paths": ["README.md"]}
```
Verify it lands in coder's inbox.

### 5. Verify dispatch-gate states
- Coder with no ready file → tools allowed (BOOT)
- Create ready file → tools blocked except Read (WAITING)
- Task in inbox → tools allowed (WORKING)
- Done marker + no verdict → only git commit allowed (DELIVERED)

### 6. Verify review fan-out
Coder writes review_request to outbox. Verify:
- Watcher copies to each reviewer's inbox
- Monitor gets CC copy
- Audit log records the event

### 7. Verify commit gate
- Attempt `git commit` on protected branch with no verdict → BLOCKED
- Write approved verdict to merged_verdicts → commit ALLOWED
- Attempt on non-protected branch → ALLOWED regardless

### 8. Experiment-rig proof
Edit `config.agents[]`: add a 3rd reviewer. Change `consensus_rule` to `majority`. Re-run. Zero code changes. Everything works.

## What to check if things break

1. `GATE_AGENT_NAME` set? → `echo $env:GATE_AGENT_NAME` in agent terminal
2. Hooks installed? → check `settings.local.json` for orchestrator entries
3. Config valid? → `orch validate`
4. Watcher running? → check launcher status or `Get-Process python`
5. Decision trace → `.orchestrator/logs/decision_trace_<session>.log`
6. Audit log → `.orchestrator/logs/audit.log`
