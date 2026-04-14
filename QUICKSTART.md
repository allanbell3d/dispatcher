# Quick Start

Start with `docs/OPERATOR_GUIDE.md` for the full operator path. This file is the deployment/setup checklist.

## Prerequisites

- Python 3.10+
- PowerShell 7 (for launcher)
- psmux (Windows) or tmux (Linux/Mac)
- Claude Code CLI

No pip install needed — engine is stdlib only.

## 1. Clone

```bash
git clone https://github.com/allanbell3d/dispatcher D:\IA\dispatcher_repo
```

## 2. Deploy to a Project

The engine repo is the source. Your project gets a copy of `.orchestrator/` and `dispatch/` folders. The engine code stays here — hooks reference this path.
The root `sprint_profiles/` directory is the deploy-time template source; live sprint profiles live under `.orchestrator/sprint_profiles/` in each project.

```powershell
# Option A: use the launcher
pwsh -NoProfile -File bin/orch_launcher.ps1
# (preferred; `bin/launch.ps1` and `bin/launch.sh` are legacy fossils)
# → Install Options → Deploy to Project → pick your project folder

# Option B: manual
# 1. Copy .orchestrator/ to <your-project>/.orchestrator/
# 2. Edit <your-project>/.orchestrator/config.json for your team/paths
# 3. Install hooks:
python scripts/install_hooks.py --all --project <your-project>
```

## 3. Configure

Edit `<your-project>/.orchestrator/config.json`:

- `agents[]` — who participates (names, roles, executor flag)
- `routing` — where messages go (review requests, CC, escalation)
- `gate` — consensus rule, required approvers, protected branches
- `paths` — folder locations (defaults work for most setups)
- `wake` — mechanism (psmux/tmux), timing, thresholds

See `schemas/config_schema.json` for the full schema.

## 4. Validate

```bash
python scripts/doctor.py <your-project>
python scripts/validate.py <your-project>
python scripts/sprint_ready.py <your-project>
```

Doctor checks prerequisites. Validate checks install/runtime health. Sprint-ready is the strict preflight for a live sprint.

Use `validate.py` after deployment. Use `sprint_ready.py` only once tasks are loaded and you are about to run a real sprint.

## 5. Launch a Sprint

```powershell
pwsh -NoProfile -File bin/orch_launcher.ps1
```

The launcher:
1. Validates config and lets you run a separate sprint-ready check
2. Creates dispatch folders for all agents
3. Starts the watcher (background supervisor loop)
4. Opens psmux terminals per agent with `GATE_AGENT_NAME` set
5. Optionally launches Claude Code in each terminal
6. Dispatches first task from the plan

## 6. During a Sprint

The watcher handles everything automatically:
- Scans agent outboxes for messages
- Routes review requests to reviewers (fan-out)
- Collects verdicts and writes merged verdicts (fan-in)
- Dispatches next task on approval
- Escalates to Allan on timeout or max rework rounds

Manual intervention:
- **Status:** launcher dashboard or `python scripts/orchestratorctl.py status .`
- **Pause:** launcher menu or write `.flag` halt files to `.orchestrator/halts/`
- **Resume:** launcher menu or `python scripts/orchestratorctl.py resume . --agent gate-ralph [--refan]`
- **Override:** `python scripts/orchestratorctl.py override . --task TASK-123 --verdict approved --reason "operator override"` (emergency gate bypass, audit logged)
- **Stop:** create `.orchestrator/runtime_flags/STOP`

## 7. Logs

Dual-write — NAS archive + project local:

| Log | What |
|-----|------|
| `decision_trace_<session>.log` | Every hook call: agent, tool, decision, reason, timing |
| `audit.log` | State changes, fan-in events, overrides, crashes |

## Current Limitation

Live end-to-end human sprint proof is still pending. Local validation, launcher dry-run, and focused pytest coverage pass in this repo, but the mixed-agent production flow still needs Allan confirmation on a real project.
