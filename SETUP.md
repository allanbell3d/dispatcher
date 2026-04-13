# Setup

## Engine deployment

Single source in `dispatcher/orchestrator/`. Deployed to two locations:

| Location | Purpose |
|---|---|
| `W:\Claude_Library\orchestrator\` | NAS primary — hooks reference this path |
| `D:\IA\orchestrator\` | Fallback — if NAS unreachable |

Deploy = copy `dispatcher/orchestrator/*` to both locations.

## Agent profiles

| Location | Purpose |
|---|---|
| `W:\Claude_Library\agents\` | NAS primary |
| `D:\IA\agents\` | Fallback |

Coordinated profiles: `profiles/coordinated/gate-*/` (for gated sprints)
Standalone profiles: `profiles/standalone/*/` (for direct work outside sprints)

## Per-project enablement

A project with the dispatcher enabled contains:

```
<project>/
├── .orchestrator/
│   ├── config.json           ← team, routing, gates, paths
│   ├── tasks/                ← parsed tasks
│   ├── plans/                ← plan files
│   ├── diffs/                ← staged diffs for review
│   ├── merged_verdicts/      ← watcher MERGE output
│   ├── halts/                ← halt flags
│   ├── runtime_flags/        ← STOP file, hook toggles, session ID
│   ├── trackers.json         ← fan-in state
│   ├── logs/                 ← local copy of all logs
│   └── sprint_profiles/      ← sprint_on.json + sprint_off.json for roles.json patching
├── dispatch/
│   ├── <agent>/inbox/
│   ├── <agent>/outbox/
│   ├── <agent>/reports/
│   ├── <agent>/done/
│   └── <agent>/archive/
└── (project code)
```

No engine code in the project. Hooks reference the deployed NAS/D:\ paths.

## Identity

The launcher sets `$env:GATE_AGENT_NAME` per psmux session. All hooks read this. No file-read detection (P1).

## Config

See `orchestrator/schemas/config_schema.json` for the full schema. Key sections:
- `agents[]` — who participates
- `routing` — message routing rules
- `gate` — consensus rule, protected branches, required approvals
- `paths` — all folder locations (overridable)
- `wake` — mechanism, timing, thresholds

## Logs

Dual-write to NAS (`W:\Claude_Library\orchestrator\logs\<project>\`) and project-local (`.orchestrator/logs/`). NAS = archive, project = backup + agent access.
