# Dispatcher — Gated Multi-Agent Sprint Engine

**Version:** 0.1.9
**Spec:** `docs/specs_frozen/MASTER_SPECS_MERGED.md` v2.4
**Status:** Waves 1-3 complete. Wave 4 in progress.

## What This Is

A dispatch + gate engine that runs gated multi-agent sprints. One coder does the work, reviewers block commits that don't match the spec, a monitor watches live and halts drift. Config-driven — zero code changes between experiments.

## Project Structure

```
dispatcher/
├── orchestrator/          ← engine code (single source, deployed to NAS + D:\)
│   ├── hooks/             ← dispatch_gate, inbox_access_guard, monitor_ingest, check_gate, etc.
│   ├── lib/               ← common.py (resolve_path, audit_log, halt helpers), wake.py
│   ├── scripts/           ← watcher.py, validate.py, install_hooks.py, orchestratorctl.py
│   ├── schemas/           ← config_schema.json, task_schema.json, plan_schema.json
│   ├── bin/               ← orch_launcher.ps1, launch.ps1/sh
│   ├── tests/             ← per-component subprocess tests
│   └── mcp-server/        ← frozen, not wired
├── agents/profiles/       ← coordinated/gate-*/role_prompt.md, standalone/*/CLAUDE.md
├── .orchestrator/         ← per-project engine-private state (config, tasks, plans, diffs, logs)
├── dispatch/              ← per-agent inbox/outbox/reports/done/archive
├── docs/                  ← specs, plans, reviews, ref docs
└── memory/                ← per-agent session memory
```

## Quick Reference

| What | Where |
|---|---|
| Master spec | `docs/specs_frozen/MASTER_SPECS_MERGED.md` |
| KISS rules | `docs/specs_frozen/MASTER_KISS_follow_Allways_spec.md` |
| Hook guide | `docs/specs_frozen/HOOK_SYSTEM_ORCHESTRATOR_GUIDE.md` |
| Launcher spec | `docs/specs_frozen/LAUNCHER_SPEC.md` |
| Liveness spec | `docs/specs_frozen/LIVENESS_SPEC.md` |
| Build plan | `docs/plans/ROUND4_ORCHESTRATOR_BUILD_PLAN.md` |
| Config | `.orchestrator/config.json` |
| Config schema | `orchestrator/schemas/config_schema.json` |

## Rules (from spec — read the full list there)

- No hardcoded agent names, paths, team composition, or wake mechanism
- Stdlib only in engine code. Zero pip deps.
- `resolve_path()` for all path resolution (not deprecated `resolve_paths()`)
- P3: every hook exits 0 immediately without `GATE_AGENT_NAME`
- P4: enforcement hooks fail-secure (exit 2), advisory hooks fail-open (exit 0)
- P7: atomic writes for all state files
- Shebang line 1 on every `.py`
- 4 survival questions per function: irreducible? absorbable? config lookup? over-engineering?
