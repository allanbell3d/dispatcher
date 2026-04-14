# Wave 5 Execution Runbook

## Goal

Run the first real gated sprint on Dubizzle using the live dispatcher engine, one active coder, the selected reviewer preset, monitor visibility, and watcher-driven mail delivery.

## Order

1. validate install/runtime health
2. install hooks if needed
3. confirm reviewer preset
4. load the current task/batch
5. run sprint-ready preflight
6. start watcher
7. start active agents
8. confirm monitor inbox activity
9. execute the sprint
10. capture results in `WAVE5_RESULTS_TEMPLATE.md`

## Commands

```powershell
python scripts/validate.py .
python scripts/sprint_ready.py .
python scripts/orchestratorctl.py reviewers show .
python scripts/install_hooks.py --all --project .
python scripts/orchestratorctl.py sprint-ready .
pwsh -NoProfile -File bin/orch_launcher.ps1
```
