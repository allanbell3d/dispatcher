# Wave 5 Execution Runbook

## Goal

Run the first real gated sprint on Dubizzle using the live dispatcher engine, one active coder, the selected reviewer preset, monitor visibility, and watcher-driven mail delivery.

## Order

1. validate config and hooks
2. confirm reviewer preset
3. start watcher
4. start active agents
5. load the current task/batch
6. confirm monitor inbox activity
7. execute the sprint
8. capture results in `WAVE5_RESULTS_TEMPLATE.md`

## Commands

```powershell
python scripts/validate.py .
python scripts/orchestratorctl.py reviewers show .
python scripts/install_hooks.py --all --project .
pwsh -NoProfile -File bin/orch_launcher.ps1
```
