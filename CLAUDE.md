# Dispatcher — Claude Code Instructions

**Version:** 0.1.10
**Spec:** `docs/architecture/MASTER_SPECS_MERGED.md` v2.4

## What This Is

A gated multi-agent sprint engine. File-based dispatch, mechanical approval gates, config-driven everything. See [README.md](README.md) for the full picture.

## Repo Structure

```
dispatcher/
├── hooks/                  8 Python hook scripts (enforcement + advisory)
├── scripts/                watcher, install_hooks, validate, doctor, orchestratorctl, send
├── lib/                    common.py (resolve_path, audit_log, trace_hook, halt helpers), wake.py
├── schemas/                config_schema.json, task_schema.json, plan_schema.json
├── bin/                    orch_launcher.ps1 (primary PowerShell 7 GUI; launch.ps1/launch.sh are legacy fossils)
├── tests/                  per-component subprocess tests
├── .orchestrator/          engine-private state (config, tasks, plans, halts, logs, verdicts)
├── dispatch/               per-agent: gate-ralph/, gate-architect/, etc. → inbox/outbox/reports/done/archive
├── agents/profiles/        coordinated (gate-*/) and standalone agent profiles
├── docs/architecture/      canonical specs (MASTER_SPECS_MERGED, KISS)
├── docs_dev/               reviews, plans, ref docs, specs_frozen/, legacy artifacts
├── memory/                 per-agent session memory
└── mcp-server/             frozen — not wired
```

## Specs (Source of Truth)

| What | Where |
|------|-------|
| Master spec | `docs/architecture/MASTER_SPECS_MERGED.md` |
| KISS rules | `docs_dev/specs_frozen/MASTER_KISS_follow_Allways_spec.md` |
| Hook guide | `docs_dev/specs_frozen/HOOK_SYSTEM_ORCHESTRATOR_GUIDE.md` |
| Launcher spec | `docs_dev/specs_frozen/LAUNCHER_SPEC.md` |
| Liveness spec | `docs_dev/specs_frozen/LIVENESS_SPEC.md` |
| Config schema | `schemas/config_schema.json` |

## Rules (Non-Negotiable)

1. **No hardcoded agent names, paths, team composition, or wake mechanism** — everything from config
2. **Stdlib only** — zero pip dependencies in engine code
3. **`resolve_path()`** for all path resolution
4. **P3:** every hook exits 0 immediately without `GATE_AGENT_NAME`
5. **P4:** enforcement hooks fail-secure (exit 2), advisory hooks fail-open (exit 0)
6. **P7:** atomic writes — tmp + rename for all state files
7. **Shebang** `#!/usr/bin/env python3` on line 1 of every `.py`
8. **Gate-prefixed names everywhere** — `gate-ralph`, `gate-architect`, etc. No stripping, no building.
9. **4 survival questions per function:** irreducible? absorbable? config lookup? over-engineering?
10. **Surgical edits only** — no file rewrites unless legacy is fundamentally incompatible with spec

Halt flags are `.flag` files in `.orchestrator/halts/`.

## Identity Model

- `agents[].name` in config = full gate-prefixed name
- `GATE_AGENT_NAME` env var = full gate-prefixed name
- `dispatch/<gate-name>/inbox/` = full gate-prefixed folder
- No `strip_gate_prefix()` — delete if found

## Known Issues (as of 0.1.10)

The codebase has 14 verified issues blocking production use. The #1 blocker is the sys.path bootstrap — `parents[0]` should be `parents[1]` in all hooks/ and scripts/. See [STATE.md](STATE.md) for the full fix list.

## Commands

```bash
# Validate config against schema
python scripts/validate.py .

# Check prerequisites
python scripts/doctor.py .

# Install hooks for all agents
python scripts/install_hooks.py --all

# Sprint status
python scripts/orchestratorctl.py status .

# Launch GUI
powershell -File bin/orch_launcher.ps1
```

Note: all Python commands currently fail with ModuleNotFoundError (bootstrap issue #1).
