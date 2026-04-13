# Dispatcher

**A gated multi-agent sprint engine.**

Dispatcher puts a system in place so AIs cannot fuck up a build. It enforces review and spec-driven development through mechanical gates — not trust, not conventions, not "please review before merging."

One coder does the work. Reviewers block the commit if it doesn't match the spec. A monitor watches the coder live and halts it mid-session if it drifts. The coder never sees the plan — it gets one task at a time via its inbox.

Primary operator UI: `bin/orch_launcher.ps1`. The older `bin/launch.ps1` and `bin/launch.sh` scripts are legacy fossils and should not be used for new work.

It is an **experiment rig, not a product.** Zero code changes between experiments. Team composition, routing rules, consensus model, wake timing, folder paths — all from `config.json`.

> *"A dispatcher, completely agnostic, completely transparent, stateless, reliable — something that puts a system in place so AIs cannot fuck up a build."*
>
> *"Keep it simple stupid. No extra code. Gated reviews. Flexible. Powerful but simple."*

---

## The Sprint Lifecycle

```
1. Allan writes a plan                    (50 tasks in .orchestrator/plans/)
2. Launcher starts agent sessions         (psmux terminals, one per agent)
3. Watcher dispatches Task 1              → gate-ralph/inbox/
4. gate-ralph works                       dispatch_gate controls tool access per state
5. gate-ralph delivers                    writes review_request to outbox/
6. Watcher fans out                       → gate-architect/inbox/ + gate-critic/inbox/
7. Both reviewers approve                 verdicts land in watcher via outbox/
8. Watcher writes merged_verdict          unanimous consensus met
9. check_gate allows merge                commit to protected branch unblocked
10. Watcher dispatches Task 2             cycle repeats
```

If either reviewer rejects: rework request goes back to gate-ralph. Max 3 rounds, then escalate to Allan.

---

## The Gate Model

**What gets gated:** merges to protected branches (`dev`, `main`).
**What doesn't:** commits to work branches — ungated, fast iteration.

```
┌─────────────────────┐
│   dispatch_gate     │  PreToolUse — controls which tools the coder can use
│   (enforcement)     │  BOOT → WAITING → WORKING → DELIVERED
└─────────────────────┘
┌─────────────────────┐
│   check_gate        │  PreToolUse — blocks git commit on protected branches
│   (enforcement)     │  until merged_verdict exists with unanimous approval
└─────────────────────┘
┌─────────────────────┐
│   inbox_access_guard│  PreToolUse — blocks coder from reading .orchestrator/,
│   (enforcement)     │  other agents' inboxes, plans, reviewer reports
└─────────────────────┘
```

Enforcement hooks fail-secure: if anything is wrong (malformed input, missing config, bad identity), they **block**. Advisory hooks (monitor_ingest, activity_logger, on_file_message, stop_notify) fail-open: if they break, the coder keeps working.

---

## Agents

| Agent | Role | What it does |
|-------|------|-------------|
| **gate-ralph** | Coder (executor) | Writes code. Gets one task at a time. Cannot see the plan. Cannot read reviewer reports. |
| **gate-architect** | Reviewer | Reviews diffs for spec compliance, architecture decisions, contract alignment. |
| **gate-critic** | Reviewer | Reviews diffs for correctness, edge cases, KISS violations, over-engineering. |
| **gate-monitor** | Monitor | Watches coder activity live via PostToolUse hooks. Halts on drift. CC'd on everything. |
| **gate-playwright** | Tester | Runs E2E tests after each batch completes. Results route back to gate-ralph. |

Agent names are gate-prefixed everywhere. No stripping, no building, no transformation. What's in config is what's in the env var is what's in the dispatch folder name.

---

## Repo Structure

```
dispatcher/
├── hooks/                  8 Python hook scripts (the enforcement + advisory layer)
├── scripts/                watcher.py, install_hooks.py, validate.py, doctor.py, orchestratorctl.py
├── lib/                    common.py (resolve_path, audit_log, trace_hook, halt helpers), wake.py
├── schemas/                config_schema.json, task_schema.json, plan_schema.json
├── bin/                    orch_launcher.ps1 (PowerShell 7 GUI launcher)
├── tests/                  per-component subprocess tests
│
├── .orchestrator/          engine-private state (config, tasks, plans, halts, logs, verdicts)
├── dispatch/               per-agent comms: gate-ralph/, gate-architect/, etc.
│   └── <agent>/            inbox/ outbox/ reports/ done/ archive/
│
├── agents/profiles/        coordinated (gate-*/) and standalone agent profiles
├── docs/architecture/      canonical specs (MASTER_SPECS_MERGED, KISS, Hook Guide, Launcher, Liveness)
├── docs_dev/               reviews, plans, ref docs, legacy artifacts
├── memory/                 per-agent session memory
└── mcp-server/             frozen — not wired, not deleted
```

The root `sprint_profiles/` directory is the deploy-time template source. Live sprint profiles live under `.orchestrator/sprint_profiles/` in each project.

### Three-Tier Access Model

| Tier | Path | Who can access | Purpose |
|------|------|---------------|---------|
| Engine-private | `.orchestrator/` | Engine only (watcher, hooks) | Config, state, verdicts, plans, logs |
| Agent-facing | `dispatch/<agent>/` | Owning agent + watcher | Inbox/outbox message passing |
| Project code | Everything else | All agents | The actual codebase being built |

`inbox_access_guard` enforces this at the tool level — blocks Read, Grep, Glob, AND Bash command strings targeting protected paths.

Halt flags use `.flag` files in `.orchestrator/halts/`.

---

## Config-Driven Everything

All behavior comes from `.orchestrator/config.json`. The schema is at `schemas/config_schema.json`.

```json
{
  "agents": [
    { "name": "gate-ralph", "profile": "gate-ralph", "executor": true, "roles": ["coder"] },
    { "name": "gate-architect", "profile": "gate-architect", "executor": false, "roles": ["reviewer"] }
  ],
  "gate": {
    "require_approvals_from": ["gate-architect", "gate-critic"],
    "consensus_rule": "unanimous",
    "max_rework_rounds": 3,
    "protected_branches": ["dev", "main"]
  },
  "routing": {
    "review_requests_to": ["gate-architect", "gate-critic"],
    "cc_all": ["gate-monitor"],
    "escalation_target": "allan"
  }
}
```

Want 3 reviewers instead of 2? Add them to `agents[]` and `gate.require_approvals_from`. Want majority instead of unanimous? Change `consensus_rule`. Want to gate `staging` too? Add it to `protected_branches`. Zero code changes.

---

## Specs (Source of Truth)

| Document | What it defines |
|----------|----------------|
| [MASTER_SPECS_MERGED.md](docs/architecture/MASTER_SPECS_MERGED.md) | 21 components, 32 hard rules, 13 FLAGs — the complete engine contract |
| [MASTER_KISS_follow_Allways_spec.md](docs_dev/specs_frozen/MASTER_KISS_follow_Allways_spec.md) | 4 survival questions per function, 6 coding rules |
| [HOOK_SYSTEM_ORCHESTRATOR_GUIDE.md](docs_dev/specs_frozen/HOOK_SYSTEM_ORCHESTRATOR_GUIDE.md) | Hook engineering principles P1-P8, wiring contract |
| [LAUNCHER_SPEC.md](docs_dev/specs_frozen/LAUNCHER_SPEC.md) | 38 menu items, sprint wizard, install submenu |
| [LIVENESS_SPEC.md](docs_dev/specs_frozen/LIVENESS_SPEC.md) | Smart wake — only wake agents with inbox items AND idle |

---

## Hard Rules (subset — full list in spec)

1. No hardcoded agent names, team composition, folder paths, or wake mechanism
2. Stdlib only — zero pip dependencies
3. The coder NEVER sees the plan
4. Mechanical enforcement, not trust — hooks physically block tool calls
5. Nothing is ever deleted — logs, dispatch history, archives are permanent
6. Every function must justify its existence (4 survival questions)
7. Enforcement hooks fail-secure, advisory hooks fail-open
8. Single writer per file — no merge logic, no locks
9. Atomic writes — tmp + rename for all state files
10. Windows-safe paths — `pathlib.Path` only

---

## Current Status

**Version:** 0.1.10
**Waves 1-4:** code-complete
**Production-ready:** No

14 known issues identified by GPT review, Codex audit, and hookmaster live testing. The top blocker is the Python import bootstrap — `sys.path` resolves wrong, so no hook or script actually runs. See [CHANGELOG.md](CHANGELOG.md) for the full issue list and fix priorities.

---

## Quick Start

See [QUICKSTART.md](QUICKSTART.md).

## License

Private. Allan Bell.
