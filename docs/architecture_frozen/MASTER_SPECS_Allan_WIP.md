Referenced files located at `\ref_docs`

## Validity

** This document is valid and active **


## Architecture decisions (locked)

| Decision | Value | Rationale |
|----------|-------|-----------|
| Engine location | `W:\Claude_Library\orchestrator\` (NAS, primary) | Shared across all projects |
| Engine fallback | `D:\IA\orchestrator\` | If NAS is down |
| Agent profiles location | `W:\Claude_Library\agents\` (primary), `D:\IA\agents\` (fallback) | Same logic |
| Config per project | `<project_root>/.orchestrator/config.json` | Project declares its team, routing, gates |
| Dispatch folder | `<project_root>/dispatch/<agent>/` with `inbox/`, `outbox/`, `reports/`, `done/`, `archive/` | Reusing existing naming convention |
| Ready-file location | `dispatch/<agent>/ready` | Agent-writable, matches startup_protocol |
| MCP status | **Frozen** — code stays, not wired, not deleted, not offered as an option | Not ready. Noise. Revisit later. |
| Executor default | `false` — explicit opt-in via `agents[].executor` in config | Least privilege |
| Dependencies | Zero pip deps — stdlib only | Engine stays self-contained |
| Deletion policy | Nothing is ever deleted — logs, archives, dispatch history are permanent | The record is the record |

## Design decisions (closed — do not reopen)

| # | Question | Answer |
|---|----------|--------|
| Q1 | WAITING phase tool access | Allow Read, block everything else. Read not in the PreToolUse matcher so the hook never fires for it. |
| Q2 | Ready-file path | `dispatch/<agent>/ready` |
| Q3 | Monitor ingest payload | Standard Claude Code PostToolUse stdin JSON. Parsed by `hook_input()`. No custom schema. |
| Q4 | Config validator approach | Hand-roll Python. No pip deps. |
| Q5 | Executor field default | `false`. Opt-in. |
| Q6 | Inbox guard scope | Block `dispatch/<other_agent>/*` — full folder isolation. |

## Constraints (apply to every item)

1. No new pip dependencies
2. No hardcoded agent names anywhere in engine code — names come from config or env vars only
3. No hardcoded role behaviors — the engine does not define what agents do
4. No hardcoded project paths — resolved from config `shared_roots`, env vars, or CLI args
5. Surgical edits only — no file rewrites
6. All `.py` files must pass `python -m py_compile <file>` exit 0
7. Windows path compat — `pathlib.Path` only, no hardcoded `/` in path construction
8. Shebang `#!/usr/bin/env python3` on line 1 of every `.py` file, `sys.path` block after
9. Every function must justify its existence — if it can be deleted or combined, it should be
10. MCP is frozen — do not wire, do not delete, do not reference as available functionality

---

# Allans requirements

- Aprovals should be reliable, both aprove and reject. 
- Aprovals should be overridable

---


**From: orchestrator_finish_pass_prd.md** 

File worh considering, priotizinng sections and using as requiremts for coding.

## Story ENG-1: Config schema validator
Capture chema for what we are building, before or after

## Story ENG-2: Dispatch-gate hook (state machine)
Consider and apply as KISS

## Story ENG-3: Executor scope fix
Apply

## Story ENG-4: Inbox access guard
Apply

## Story ENG-5: Monitor ingest hook
Worth considering

## Story ENG-6: Watcher crash reporting
Deffer

## Story ENG-7: Watcher activity-log tailing
## Story ENG-8: Activity logger cleanup
to consolidate all in 1 logging system


## Story ENG-9: Work-package validator (anti-lies)
to be considered after poc

## Story ENG-10: One-shot hook installer
to be built after poc

## Story ENG-11: Config flag updates
Not sure of purpose

## Story ENG-12: Smoke test hardening
yes but down the line


---

**From: IMPROVEMENT_IDEAS_hook-master_2026-04-10** 

File worh considering, priotizinng sections, update nuances and use it as requiremts for coding.

# IMPROVEMENT_IDEAS_hook-master_2026-04-10 — commented against `ready_orchestrator_setup_2026-04-10`

Status legend:
-
-
-

Intent legend:
- KEEP - to be kept and not removed,used to drive specs and acceptance. needs to be checked.
- BUILD - to implement now
- DEFFER - to be built later
- REJECT - delete  


## Overall comment

This document was mostly forward-looking. The ready bundle implements a meaningful subset of the deployment, portability, helper-command, and hook-filtering recommendations, but most of the bigger operator/safety/optimization ideas are still future work.

## 1. Functionality

### 1.1 Operator controls (pause / resume / replay / drain)
**Decision:** - KEEP

### 1.2 Queue visibility (`queue_status.json`, status CLI)
**Decision:** - KEEP

### 1.3 Rollback / reopen support
**Decision:** - KEEP

### 1.4 Rich task definitions
**Decision:** - KEEP 

**Comment:** Existing task files are still JSON and project-local, but there is no dependency/blocker/tag/effort/assignee system added in the ready bundle.

### 1.5 Multi-sprint support
**Decision:** - DEFFER

### 1.6 Agent handoff protocol
**Decision:** - DEFFER

### 1.7 External integrations
**Decision:** - DEFFER

## 2. Compatibility

### 2.1 Hardcoded project paths
**Decision:** - KEEP 

**Comment:** This was one of the strongest improvements in the ready bundle. Shared roots and project paths are now resolved centrally with primary/fallback logic.

### 2.2 Python version lock
**Decision:** - KEEP 

**Comment:** `doctor.py` checks Python 3.10+.

### 2.3 TypeScript / Bun dependency
**Decision:** - KEEP 

**Comment:** The MCP server is still Bun-based. `doctor.py` at least checks for Bun/Node availability.

### 2.4 Cross-platform tmux/psmux
**Decision:** - KEEP 

**Comment:** `doctor.py` checks for `psmux`/`tmux`, and the watcher probes available multiplexers. There is still no richer non-mux orchestration mode beyond degraded operation.

### 2.5 Abstract project from bundle
**Decision:** - BUILD

**Comment:** The ready bundle does separate shared engine roots from project roots. It is not yet packaged as a pip-installable engine/template system.

### 2.6 Config schema
**Decision:** - BUILD

## 3. Ease of Deployment

### 3.1 One-command bootstrap
**Decision:** - KEEP 

**Comment:** Not a full bootstrap, but there is a usable setup skeleton plus helper commands.

### 3.2 Dependency probe (`doctor`)
**Decision:** - KEEP 

### 3.3 Install hooks automatically
**Decision:** - KEEP 

**Comment:** A helper exists to render/install hook JSON, but it is not a fully automatic per-agent end-to-end installer.

### 3.4 Self-test after install
**Decision:** - BUILD 

**Comment:** `validate.py` and `dispatch_contract_smoke.py` exist, but not the richer full self-test suite described here.

### 3.5 Uninstall / teardown
**Decision:** - DEFFER

### 3.6 Versioning + upgrade path
**Decision:**  - BUILD

## 4. Safety

### 4.1 Dry-run mode
**Decision:** -  DEFFER

### 4.2 Audit trail
**Decision:** - TBD

**Comment:** Basic persistent logs exist, but no dedicated append-only audit log.

### 4.3 Signed approvals
**Decision:** - TBD

### 4.4 Diff hash binding
**Decision:** - DELETE

**Comment:** Supported if an approval includes `diff_sha256`, but not enforced as a fully signed or always-required policy.

### 4.5 PII / secret scanning in messages
**Decision:** - DELETE

### 4.6 Max message size 
**Decision:** - DELETE

### 4.7 Rate limiting
**Decision:** - DELETE

### 4.8 Sandbox / test mode
**Decision:** - DELETE 

### 4.9 Secret redaction in logs
**Decision:** - DELETE

**Comment:** `activity_logger.py` redacts some obvious token patterns, but this is not a full secret hygiene system across logs and dispatch payloads.

## 5. Optimization

### 5.1 Filesystem events instead of polling
**Decision:** - BUILD 

### 5.2 Async I/O in MCP server
**Decision:**

### 5.3 Config cache with mtime check
**Decision:** IN PRACTICE -  - KEEP 

**Comment:** The ready watcher loads config once at startup instead of repeatedly every loop.

### 5.4 Batch processing
**Decision:** - DEFFER

### 5.5 SQLite for state
**Decision:** - DEFFER

### 5.6 Compile-once for TypeScript
**Decision:** - DEFFER

### 5.7 Lazy memory folder creation
**Decision:** NOT RELEVANT /

## 6. Hook Optimization

### 6.1 `matcher` filtering
**Decision:**  - KEEP - CHECK

### 6.2 `if` filtering
**Decision:** - KEEP - CHECK

### 6.3 async logger
**Decision:** - KEEP - CHECK

### 6.4 `asyncRewake` for dispatch notifications
**Decision:** - EXPLAIN

### 6.5 `once: true`
**Decision:** - EXPLAIN

### 6.6 Skip hooks for subagents 
**Decision:** - BUILD

**Comment:** in `activity_logger.py`, not consistently across all hooks.

### 6.7 Hook-level kill switch
**Decision:** - BUILD

### 6.8 Combined hook dispatcher
**Decision:** - BUILD

### 6.9 Hook result caching
**Decision:** - BUILD EXPLAIN

### 6.10 Regex matcher cleanup
**Decision:** - BUILD

**Comment:** Basic matcher usage is there, but not a broad cleanup pass.

## 7. New hook ideas

### 7.1 PreReview hook
**Decision:** - EXPLAIN - CONSIDER

### 7.2 PostReview hook
**Decision:** - EXPLAIN - CONSIDER

### 7.3 Compaction hook
**Decision:** - EXPLAIN - CONSIDER

### 7.4 Interrupt hook
**Decision:** - EXPLAIN - CONSIDER

### 7.5 Health check hook
**Decision:** - EXPLAIN - CONSIDER

## 8. Meta priorities
**Comment:** The ready bundle did follow some of the right priorities:
- path compatibility
- doctor/validate
- hook filtering
- stronger gating

But it did not yet reach the larger safety/operability items like schema validation, audit trail, or SQLite.

## 9. Things not to do
**Comment:** No conflict here. The ready bundle did not overbuild a web UI or add unnecessary agent types.

## Extra comment tied to your current requirement

The improvement list did not explicitly describe your Ralph JSON → monitor parser, but in practice that should now be added as one of the next concrete hooks/scripts:
- ingest Ralph structured JSON
- normalize it
- emit a monitor-facing dispatch artifact
- optionally archive the raw JSON separately

That feature is still **not implemented**. - BUILD

---

**From: IMPLEMENTATION_STATUS_SUMMARY_2026-04-10** 

feaaures to keep and convert in to spec and requirements


### Implemented - needs to be check and updated with KISS if needed. 
- Shared orchestrator root with primary/fallback resolution (`W:` first, `D:` fallback)
- Shared agents root with primary/fallback resolution
- Project-local `dispatch/`, `memory/`, `docs/`, `.orchestrator/`
- `gate-*` coordinated profiles separated from standalone profiles
- Common path resolver (`lib/common.py`)
- Hook payload field fix for `activity_logger.py`
- Hook rendering/installation helper (`install_hooks.py`)
- Basic helper wrapper commands (`orchestratorctl.py`, `orch.ps1`, `COMMANDS.md`)
- `doctor.py`
- Improved `validate.py`
- Improved smoke test
- Task advancement no longer fires on every successful commit; it now requires a task tag
- Approval filenames are now strict `taskid-agent.json`
- Approval task matching is strict
- Tracker persistence across watcher restart (`.orchestrator/runtime/trackers.json`)
- Hardcoded legacy path check moved into config-driven forbidden patterns
- Stop notification uses a wrapper script instead of chained shell commands

### Partially implemented - needs to be added now
- Hook optimization: matcher / `if` / async logging are used, but there is no single dispatcher, no global kill switch, and no broad caching layer

### Partially implemented - to keep and add later
- Monitor feed
- Approval safety. keep basic remove noise
- Fan-in race handling: unmatched reports are left in place with a warning instead of being silently consumed, but there is no pending-report buffer
- Duplicate-consumer problem: mitigated because MCP no longer auto-watches `active/`, but both `on_file_message.py` and MCP `read_active` can still consume files
- Session logging: watcher log and per-agent activity logs exist, but there is no dedicated immutable audit log

### Partially implemented - to remove
- Secret handling: activity logs redact some obvious tokens, but message-bus delivery itself is not scanned for secrets


### Not implemented - To ADD NOW
- structured JSON parsing from Ralph into monitor
- Ready-file startup gate exists in config, but defaults to off *ADD* 

### Not implemented - For latter
- Full config schema validation
- SQLite state backend
- Queue status CLI / `queue_status.json`
- Replay / pause / drain operator controls
- Dedicated audit trail file is not implemented
- Automatic hook install into every live agent setup is helped, but still requires the output to be placed in the agent settings file
- Full self-test with restart recovery / timeout scenarios / malformed message scenarios

