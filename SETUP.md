# Setup

## Engine Deployment

The engine source lives at `D:\IA\dispatcher_repo` (this repo). It gets deployed to two locations for runtime use:

| Location | Purpose |
|----------|---------|
| `W:\Claude_Library\orchestrator\` | NAS primary — hooks reference this path |
| `D:\IA\orchestrator\` | Fallback — if NAS is unreachable |

Deploy = copy engine files (hooks/, scripts/, lib/, schemas/, bin/) to both locations.

The launcher handles this via **Install Options → Deploy Engine**. Use `bin/orch_launcher.ps1`; `bin/launch.ps1` and `bin/launch.sh` are legacy fossils.

## Agent Profiles

Profiles are deployed separately from the engine:

| Location | Purpose |
|----------|---------|
| `W:\Claude_Library\agents\` | NAS primary |
| `D:\IA\agents\` | Fallback |

Coordinated profiles (`gate-*/`) are used during gated sprints.
Standalone profiles are used for direct work outside sprint context.

## Per-Project Setup

A project with the dispatcher enabled contains:

```
<project>/
├── .orchestrator/
│   ├── config.json             team, routing, gates, paths
│   ├── tasks/                  parsed tasks + current_task.json
│   ├── plans/                  plan files (task lists)
│   ├── diffs/                  staged diffs for review
│   ├── merged_verdicts/        watcher MERGE output
│   ├── halts/                  gate-ralph.flag, gate-architect.flag, etc.
│   ├── runtime_flags/          STOP file, hook toggles, PID files
│   ├── trackers.json           fan-in state (watcher-owned)
│   ├── logs/                   local copy of decision trace + audit
│   ├── sprint_profiles/        sprint_on.json + sprint_off.json
│   └── audit.log               append-only audit trail
├── dispatch/
│   ├── gate-ralph/             inbox/ outbox/ reports/ done/ archive/
│   ├── gate-architect/         inbox/ outbox/ reports/ done/ archive/
│   ├── gate-critic/            inbox/ outbox/ reports/ done/ archive/
│   ├── gate-monitor/           inbox/ outbox/ reports/ done/ archive/
│   └── gate-playwright/        inbox/ outbox/ reports/ done/ archive/
└── (project code)
```

No engine code in the project. Hooks reference the deployed engine at NAS/D:\ paths.

The root `sprint_profiles/` directory in this repo is the deploy-time template source. The live sprint profiles are the project-local `.orchestrator/sprint_profiles/` copies.

## Identity

The launcher sets `$env:GATE_AGENT_NAME` per psmux session. Every hook reads this for identity. No file-read detection (P1 principle).

Gate-prefixed everywhere: `gate-ralph` in config = `gate-ralph` in env = `dispatch/gate-ralph/`.

## Config

Full schema at `schemas/config_schema.json`. Key sections:

| Section | What it controls |
|---------|-----------------|
| `agents[]` | Who participates — name, profile, executor flag, roles |
| `routing` | Message routing — review targets, CC list, escalation, test results |
| `gate` | Consensus rule, required approvers, max rework rounds, protected branches |
| `paths` | All folder locations (overridable, defaults work for standard layout) |
| `wake` | Mechanism (psmux/tmux), timing, retry, idle thresholds |
| `session` | Ready files, halt between batches, session prefix, timezone |
| `fan_in` | Review timeout, required reviewers, timeout action |
| `shared_roots` | NAS/fallback paths for engine and agent profiles |

## Logs

Dual-write:
- **NAS archive:** `W:\Claude_Library\orchestrator\logs\<project>\`
- **Project local:** `.orchestrator/logs/`

NAS = permanent archive. Project local = backup + agent access during sprint.

| File | Content |
|------|---------|
| `decision_trace_<session>.log` | Every hook call — agent, tool, command, decision, reason, elapsed_ms |
| `audit.log` | State transitions, fan-in events, overrides, watcher crashes |
