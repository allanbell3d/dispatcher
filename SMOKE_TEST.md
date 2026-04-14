# Smoke Test Guide

## Automated Smoke

```bash
python scripts/dispatch_contract_smoke.py
```

Creates a temp project structure, runs message routing checks, verifies dispatch folder creation. Self-contained — no external dependencies.

---

## Manual Smoke — Full Gate Lifecycle

### 1. Pre-flight

```bash
python scripts/doctor.py .
python scripts/validate.py .
python scripts/sprint_ready.py .
```

Doctor and validate should pass on a healthy install. `sprint_ready.py` should only pass once task files exist and `current_task.json` selects a valid task.

### 2. Install Hooks

```bash
python scripts/install_hooks.py --all
```

Verify: `.claude/settings.local.json` contains orchestrator hook entries for all 8 hooks. Each enforcement hook should have the `GATE_AGENT_NAME` condition.

### 3. Launch

```powershell
powershell -File bin/orch_launcher.ps1
```

Select agents. Verify the status dashboard shows agents and watcher as running.

### 4. Dispatch a Task

Drop a task JSON into `.orchestrator/tasks/`:

```json
{
  "task_id": "SMOKE-1",
  "title": "Test task",
  "acceptance_criteria": ["File created", "Tests pass"],
  "reference_paths": ["README.md"]
}
```

Set `current_task.json` to that task, rerun `python scripts/sprint_ready.py .`, then verify the task appears in gate-ralph's inbox.

### 5. Verify dispatch_gate States

The dispatch gate controls tool access based on agent state:

| State | Condition | Tools allowed |
|-------|-----------|--------------|
| BOOT | No ready file, no task | All (agent is starting up) |
| WAITING | Ready file, no inbox task | Read only (waiting for work) |
| WORKING | Task in inbox | All (actively coding) |
| DELIVERED | Done marker, no verdict | Git commit only (waiting for review) |

Test each transition by creating/removing the appropriate files.

### 6. Verify Review Fan-Out

Have gate-ralph write a `review_request` JSON to `dispatch/gate-ralph/outbox/`. Verify:

- [ ] Watcher picks it up and copies to `dispatch/gate-architect/inbox/`
- [ ] Watcher copies to `dispatch/gate-critic/inbox/`
- [ ] gate-monitor gets a CC copy
- [ ] Tracker created in `.orchestrator/trackers.json`
- [ ] Audit log records the fan-out event

### 7. Verify Commit Gate

Test check_gate behavior:

- [ ] `git commit` on `dev` (protected) with no verdict → **BLOCKED** (exit 2)
- [ ] Write approved verdict to `.orchestrator/merged_verdicts/SMOKE-1.json` → commit **ALLOWED**
- [ ] `git commit` on a feature branch → **ALLOWED** regardless of verdict state

### 8. Verify Consensus

Write reviewer verdicts to watcher via outbox:

- [ ] One approval, one pending → no merged verdict yet
- [ ] Both approve → merged verdict written with `"decision": "approved"`
- [ ] One reject → merged verdict with `"decision": "rejected"`, rework request to gate-ralph

### 9. Experiment-Rig Proof

Edit `.orchestrator/config.json`:
- Add a 3rd reviewer to `agents[]`, `gate.require_approvals_from`, `routing.review_requests_to`
- Change `consensus_rule` to `"majority"`
- Re-run steps 6-8

Everything should work. **Zero code changes.** This is the whole point.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `ModuleNotFoundError: lib` | sys.path bootstrap — `parents[0]` should be `parents[1]` |
| Hook not firing | `GATE_AGENT_NAME` set? → `echo $env:GATE_AGENT_NAME` |
| Hook fires but no effect | Check `settings.local.json` for the hook entry |
| Config invalid | `python scripts/validate.py .` |
| Watcher not running | Launcher status or `Get-Process python` |
| Gate not blocking | Check `decision_trace` log in `.orchestrator/logs/` and confirm `.flag` halts in `.orchestrator/halts/` |
| Verdict not merging | Check `trackers.json` — are all required reviewers listed? |
| Wrong agent identity | Verify `GATE_AGENT_NAME` matches config `agents[].name` exactly |
