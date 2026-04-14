# Orchestrator — Round 1 Master Spec

**Owner:** Allan
**Written by:** gate-architect (Opus 4.6)
**Date:** 2026-04-11, updated 2026-04-12
**Version:** v2.4
**Updated:** 2026-04-13 — merged insights from 5 critic runs, 4 remediation rounds, Wave 2+3 reviews
**Sources:** Allan voice notes (2026-04-10/11), Remarks.md, MASTER_SPECS_Allan_WIP.md, MASTER_KISS_follow_Allways_spec.md, HOOK_SYSTEM_ORCHESTRATOR_GUIDE.md, orchestrator_finish_pass_prd.md, IMPROVEMENT_IDEAS_hook-master, IMPLEMENTATION_STATUS_SUMMARY, Wave 1 reviews, allan_notepad.md session transcript

---

## What this is

A dispatch + gate engine that lets Allan run a gated multi-agent sprint reliably. One coder does the work; reviewers block the commit if it doesn't match the spec; a monitor watches the coder live and halts it mid-session if it drifts.

It is an **experiment rig, not a product**. Zero code changes between experiments. All team composition, routing, consensus rules, wake mechanism, AND folder paths come from config.

> *"A dispatcher, like we did last time, completely agnostic, completely transparent, stateless, reliable — something that puts a system in place so AIs cannot fuck up a build and enforces review and spec-driven development."*

> *"Keep it simple stupid. No extra code. Gated reviews. Flexible. Powerful but simple. Think in advance."*

---

## What this is NOT

- Not a workflow engine — it doesn't decide what happens after a dispatch
- Not a role system — it doesn't define what agents do, only where they read and write
- Not an AI orchestrator — it doesn't prompt agents or shape their behavior
- Not an MCP-first system — MCP stays alive, not wired, not required for round 1
- Not a product — not sold, not hardened for untrusted environments, not scaled for multi-user
- Not a replacement for code review — reviewers do that, engine just gates

---

## Hard rules (non-negotiable)

### Engine rules

1. **No hardcoded agent names in engine code.** Literal `"ralph"` / `"architect"` / `"critic"` anywhere in engine source is a bug.
2. **No hardcoded team composition.** N coders, M monitors, P reviewers — all from config.
3. **No hardcoded folder paths.** All paths from `config.paths`. Layout is a config decision.
4. **No hardcoded wake mechanism.** `config.wake.mechanism` swaps the whole system.
5. **The coder NEVER sees the plan.** Enforced via dispatch (one task at a time) AND filesystem (inbox-access-guard blocks Read, Grep, Glob, AND Bash command strings for protected paths).
6. **The proof rule is the review criterion.** Reviewers enforce on every diff: *"If you don't prove it has to live there with a real valid reason and there's no other way to replace it, it goes out."*
7. **Mechanical enforcement, not trust.** Hooks physically block tool calls when the gate isn't met.
8. **Nothing is ever deleted.** Logs, dispatch history, archived messages — permanent.
9. **Windows-safe paths.** `pathlib.Path` only. No hardcoded `/`. No drive-letter assumptions.
10. **Stdlib only in engine code.** Zero pip dependencies.
11. **When in doubt, LEAVE it in the spec and flag it.**

### Coding rules

12. **No hardcoding configurable values.** Prompts in `.md` files, config in `.json`.
13. **Don't carry over dead features.** Before implementing: "does Allan actually use this?"
14. **Define contracts first.** Interfaces before code.
15. **KISS over completeness.** Build minimal, don't implement speculatively.
16. **Every function must justify its existence.** Four survival tests: (a) truly irreducible or thin wrapper? (b) can another function absorb it? (c) is it a function or a config lookup? (d) real complexity or agent over-engineering?
17. **Surgical edits only.** No file rewrites unless justified. Exception: when legacy code is fundamentally incompatible with the spec contract (e.g., E1 check_gate rewrite from `approvals_dir` to `merged_verdicts`). When Rule 17 is violated, the task MUST document the justification.
18. **All `.py` files must pass `python -m py_compile`.**
19. **Shebang `#!/usr/bin/env python3`** on line 1, `sys.path` block after.
20. **MCP is frozen.** Do not wire, do not delete, do not reference as available.

### Hook engineering principles (from Hook System Guide)

21. **P1 — Explicit identity over detection.** Identity via `$env:GATE_AGENT_NAME` set by launcher/watcher. Never detect by file-read patterns. Priority: env var > identity file > memory-read fallback (logged as degraded).
22. **P2 — Separate authorization from approval.** Authorization (PreToolUse, exit 2 = block) is independent from approval (PermissionRequest). Orchestrator hooks are authorization only. Never check folder access in the approval hook.
23. **P3 — Opt-in activation.** Every orchestrator hook begins with: `if not os.environ.get('GATE_AGENT_NAME'): sys.exit(0)`. Zero interference with normal Claude Code sessions.

   **Exception:** `on_file_message.py` is exempt from P3 — it is advisory, never blocks, and benefits Allan's non-orchestrator sessions. Documented in the hook's source.
24. **P4 — Fail-secure for enforcement, fail-open for advisory.** Commit-gate and dispatch-gate: catch block = exit 2 ("gate error — blocked for safety"). Monitor-ingest and context injection: catch block = exit 0 (don't block the coder because logging broke).
25. **P5 = rule #1 above.** (No hardcoded names.)
26. **P6 — Single writer per file.** Each state file has exactly one canonical writer. No merge logic, no locks. Assignments: `trackers.json` — watcher only. `dispatch/<agent>/inbox/*` — watcher only. `dispatch/<agent>/outbox/*` — owning agent only. `merged_verdicts/<task_id>.json` — watcher only. `audit.log` — `audit_log()` helper only (O_APPEND for concurrent-safe append).
27. **P7 — Atomic writes for all state files.** tmp-file-and-rename: `tmp = path.with_suffix('.tmp'); tmp.write_text(content); os.replace(str(tmp), str(path))`.
28. **P8 = rule #9 above.** (Windows paths.)

### Path resolution rules (from 5 review rounds)

29. **`resolve_path(key, project_root, config)` is the canonical path API.** All new code MUST use it. `resolve_paths()` dataclass is DEPRECATED — functional after 643be7a key alignment but must not be used in new code. Callers will be migrated progressively.
30. **Smoke test configs must validate against `config_schema.json`.** All test fixtures use spec-aligned keys. Old-format keys (`dispatch_dir`, `tasks_file`, etc.) are rejected by `additionalProperties: false`.
31. **STOP file lives at `runtime_flags/STOP`**, not `runtime/STOP`. The `runtime_flags` key from `config.paths` is canonical. `runtime_dir` is a legacy key.
32. **Empty config values must not create bogus paths.** Guard against empty strings in `escalation_target`, agent names, and path keys. An empty `escalation_target` must not create `dispatch//inbox/`.

---

## Architecture decisions (locked)

| Decision | Value | Source |
|---|---|---|
| Engine source repo | `D:\IA\dispatcher_repo\` , remote `github.com/allanbell3d/dispatcher` | Allan 2026-04-12 |
| Engine deployed (primary) | `W:\Claude_Library\orchestrator\` (NAS) | Allan 2026-04-10 |
| Engine deployed (fallback) | `D:\IA\orchestrator\` | Allan 2026-04-10 |
| Engine staged during dev | `<project>/D_staged/` and `<project>/W_staged/` | Allan 2026-04-12 |
| Agent profiles (primary) | `W:\Claude_Library\agents\` | Allan 2026-04-10 |
| Agent profiles (fallback) | `D:\IA\agents\` | Allan 2026-04-10 |
| Engine-private root | `<project>/.orchestrator/` — agent-prohibited | Allan 2026-04-11 |
| Agent-facing root | `<project>/dispatch/` | existing convention |
| Per-agent subfolders | `inbox, outbox, reports, done, archive` | Allan confirmed `inbox` 2026-04-12 |
| Wake mechanism | `tmux/psmux send-keys` (configurable) | Allan 2026-04-11 |
| Injection mechanism | `UserPromptSubmit` hook + `additionalContext` | Confirmed: `coreSchemas.ts:4804, 8106`; `runAgent.ts:5520` |
| Monitor / Playwright | One agent, two jobs — configurable to split | Allan 2026-04-11 |
| MCP status | Kept alive, frozen — not wired, not deleted | Allan 2026-04-11 |
| Executor gating | `agents[].executor: true` opt-in, default `false` | existing |
| Deletion policy | Nothing ever deleted | Allan 2026-04-10 |
| Config per project | `<project>/.orchestrator/config.json` | Allan 2026-04-10 |
| Ready-file location | `dispatch/<agent>/ready` | Allan 2026-04-10 |
| Config validator | Hand-roll Python. No pip deps. | Allan 2026-04-10 |
| Hook language | Python for engine hooks. PowerShell for Allan's permission hooks. Two systems share no code at runtime. | Hook Guide 2.4 |
| Hook placement | Per-tool hooks (PreToolUse, PostToolUse) in PROJECT `settings.local.json`. Lifecycle hooks in GLOBAL `settings.json`. Global per-tool hooks do NOT fire for project actions. | Hook Guide 2.1 |

## Design decisions (closed)

| # | Question | Answer |
|---|---|---|
| Q1 | WAITING phase tool access | Allow Read, block everything else |
| Q2 | Ready-file path | `dispatch/<agent>/ready` |
| Q3 | Monitor ingest payload | PostToolUse hook extracts tool summary, writes JSON to inbox. Structured summary, not raw stdin passthrough. |
| Q4 | Config validator | Hand-roll Python. No pip deps. |
| Q5 | Executor default | `false`. Opt-in. |
| Q6 | Inbox guard scope | Block `dispatch/<other>/*` + `state_root/*`. Include Bash command scanning. Deny pathless Grep/Glob for stamped coders. |
| Q7 | Audit logging | One logging ENGINE. Multiple sinks OK. No duplicate info. No dropped info. Dual-write: NAS (`W:\Claude_Library\orchestrator\logs\<project>\`) for long-term archive + project-local (`.orchestrator/logs/`) for backup and agent access. NAS primary, project fallback if NAS unreachable. |
| Q8 | Task ordering | Sequential per plan for POC. Parallel deferred. |
| Q9 | Approvals | Reliable (both approve and reject). Overridable via emergency escape hatch (Allan-only). |

---

## The access model — three tiers

| Tier | Who can read | Who can write | Contents |
|---|---|---|---|
| **Engine-private** | Hooks (subprocess) + watcher | Hooks + watcher | Plan, tasks, task pointer, trackers, diffs, logs, merged verdicts |
| **Agent-facing** | Owning agent (+ its hooks) | Owning agent | `inbox/`, `outbox/`, `reports/`, `done/`, `archive/` |
| **Shared writable** | Any listed agent | Any listed agent | Empty. Reserved. |

Inbox-access-guard blocks Read, Grep, Glob, AND Bash (scans command strings) for protected paths. Pathless Grep/Glob denied for stamped coders. Bash path regex must match BOTH forward slashes and Windows backslashes (`[/\\]`).

**Known gap — write protection:** The guard covers reads only. A coder could `Write` to `dispatch/gate-critic/inbox/fake.md` and inject a fake message. The spec says "Who can write: Owning agent" but this is unenforced. Track for future hardening — not blocking POC.

**Inbox file format contract:** Dispatch inboxes accept both `.md` and `.json` files. `compose_message()` produces `.md` (text with headers). `monitor_ingest.py` produces `.json` (structured summaries). Tasks are JSON (F3: Locked). **Any code scanning inbox/outbox/reports MUST NOT filter by `.md` suffix only** — use `p.is_file()` or negative filter (exclude `.tmp`). The `.md`-only filter was the #1 recurring bug across Wave 2 reviews (dispatch_gate false WAITING, watcher wake-check miss, outbox scan miss).

**Watcher glob convention:** All `glob("*.md")` patterns in watcher outbox/report/inbox scanning must be `glob("*")` with `.tmp` exclusion, or explicitly documented as `.md`-only with justification. The single-writer convention (`compose_message` → `.md`) does NOT guarantee all producers use `.md` — monitor_ingest is the counter-example.

**validate.py expected-files list:** Must include ALL engine hooks — not just the original set. When a new hook is added in any wave, it MUST be added to the expected-files list in the same task. Missing hooks from the validation list means `orch validate` won't detect accidental deletion of enforcement hooks.

**Layout** (all paths overridable via config):

```
<project>/
├── .orchestrator/              ← ENGINE-PRIVATE (agent-prohibited)
│   ├── config.json
│   ├── plans/
│   ├── tasks/ + current_task.json
│   ├── trackers.json
│   ├── diffs/<task_id>.diff
│   ├── merged_verdicts/
│   ├── halts/<coder>.flag
│   ├── runtime_flags/          ← hook toggle flags
│   └── logs/                   ← unified logging output
│
└── dispatch/                   ← AGENT-FACING
    ├── <agent>/inbox/
    ├── <agent>/outbox/
    ├── <agent>/reports/
    ├── <agent>/done/
    ├── <agent>/archive/
    └── allan/...               ← escalation target
```

---

## Components — round 1

| # | Component | Status |
|---|---|---|
| 1 | **Dispatch contract** — per-agent `inbox/outbox/reports/done/archive` | Verify |
| 2 | **Dispatch-gate hook (BOOT/WAITING/WORKING/HALTED/DELIVERED)** — flat if/elif. DELIVERED uses tracker-based detection (not outbox files). `git commit` only in DELIVERED. | Wave 2 B2 + Wave 3 B3 DONE |
| 3 | **Commit-gate hook** — reads `merged_verdicts/<task_id>.json`. Work branches ungated via `protected_branches` check. Uses `resolve_path()`. Rule 17 exception: full rewrite justified (legacy `approvals_dir` incompatible). | Wave 3 E1 DONE |
| 4 | **Coder → monitor ingest** — PostToolUse writes JSON summary to monitor inbox. | Wave 1 C1 DONE |
| 5 | **Config schema validator** — hand-rolled stdlib. Cross-references agent names in gate/routing/fan_in. | Wave 2 A4 DONE |
| 6 | **Inbox access guard** — blocks state_root + cross-agent dispatch. Covers Read, Grep, Glob, Bash. Denies pathless search. Backslash-aware regex. | Wave 1 A5 DONE |
| 7 | **Health check (`orch doctor`)** | Extend |
| 8 | **Unified logging engine** — `audit_log()` helper with O_APPEND. One module, multiple sinks. | Wave 2 F1 DONE |
| 9 | **Hook install automation** — `orch install-hooks --all`, array APPEND merge. Wires dispatch_gate (all agents), monitor_ingest + check_gate (executor only), inbox_access_guard (all agents). | Wave 3 C3 DONE |
| 10 | **Watcher reliability** — try/except main loop, crash → traceback to audit_log + notify cc_all + exit 1. | Wave 3 F2 DONE |
| 11 | **Watcher COPY/MERGE/DISTRIBUTE** — COPY fan-out for review_request (Wave 2 D1 DONE). MERGE fan-in with consensus rule + guarded trackers.pop (Wave 3 D2 DONE). DISTRIBUTE existing. | DONE |
| 12 | **Smoke scenarios** — 2 real: dispatch-gate state machine + happy-path e2e. Wave 3 added 5 test files (B3, C3, D2, E1, F2). | Partial — Wave 5 completes |
| 13 | **`orch status`** — active task, inbox counts, pending fan-ins | NEW |
| 14 | **`orch resume <task_id>`** — recover stuck task | NEW |
| 15 | **Basic rich tasks** — `deps` + `assignee` only. Sequential for POC. | Wave 1 H1/H2 schemas DONE |
| 16 | **Plan format validator** — checks required keys + forbidden placeholders | Wave 2 H3 DONE |
| 17 | **Config-driven everything** — all paths, agents, routing, gate, wake from config | Waves 1-3 DONE |
| 18 | **Watcher liveness / idle-wake** — separate ticker, never blocks main loop. Inactivity wake only for POC. | NEW |
| 19 | **Hook runtime toggle** — uses Claude Code `if` field for zero-cost gating (confirmed working per Hook Guide 2.3). Hooks stay in settings.json. **POC NOTE:** Currently implemented via flag files (`runtime_flags/hooks/<name>.disabled`) checked by `is_hook_disabled()` in each hook. ~30ms overhead per disabled hook per call. `if`-field patching + combined dispatcher (6.8) deferred to post-POC. The flag-file approach works but the `if`-field requirement stands for the production version. | POC: flag files. Target: `if`-field. |
| 20 | **Cross-directory hook awareness** — must work across W:\, D:\, E:\, .worktrees\. SHOW-STOPPER. | NEW |
| 21 | **Sprint launcher** — PowerShell entry point. Validates, starts watcher, launches agents, verifies hooks. | NEW |
| 22 | **Hook decision trace log** — every orchestrator hook call logs: timestamp, agent, tool, command, hook name, decision (allow/deny), reason, response time. Single trace file. The only way to debug hooks. | NEW |

---

## Hook runtime toggle (Component 19)

Claude Code hook entries support an `if` field using permission-rule syntax. The condition is evaluated BEFORE spawning the hook process — zero cost when disabled.

```json
{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "python check_gate.py",
    "if": "Bash(git commit *)"
  }]
}
```

**Toggle mechanism:** `orch disable` does NOT remove hook entries from settings.json. Instead it updates the `if` condition to a never-matching pattern (e.g., `if: "DISABLED"`). `orch enable` restores the real condition. Hooks stay permanently registered. Zero JSON editing by hand. Zero script execution when disabled.

**Per-feature granularity:** each feature's hook entry has its own `if` condition. `orch disable commit-gate` only affects the commit-gate entry.

---

## Subagent policy

**Detection:** Claude Code passes `transcript_path` in hook input for subagents, absent for main sessions. `is_subagent = bool(data.get('transcript_path'))`.

**Policy:** Subagents spawned by a gated coder inherit the coder's `GATE_AGENT_NAME` env and dispatch state. They are NOT independent agents. Read guards bypass for subagents (they need to read code). Write guards (commit-gate, dispatch-gate) keep firing — subagents should not commit or change dispatch state.

```python
is_subagent = bool(data.get('transcript_path'))
if is_subagent and hook_type == 'read_guard':
    sys.exit(0)  # bypass
```

---

## Watcher dispatch message types

| Type | Sender | Routed to | Action |
|---|---|---|---|
| `review_request` | coder | `config.routing.review_requests_to[]` | COPY to each reviewer inbox + wake |
| `review_response` | reviewer | coder | DISTRIBUTE + check fan-in |
| `halt` | monitor | coder | Flag file OR inbox inject per `halt_mode` |
| `intervention` | monitor | any agent | DISTRIBUTE + wake |
| `escalation` | any agent | `dispatch/allan/inbox/` | DISTRIBUTE + alert |
| `test_result` | playwright | coder | DISTRIBUTE per routing |
| `handoff` | coder | next agent | DISTRIBUTE per routing |
| `done_marker` | coder | watcher | Triggers task advancement |
| `cc` | watcher | `config.routing.cc_all[]` | COPY of any routed message |

---

## Merged verdict contract

When the watcher MERGE fan-in reaches consensus, it writes a JSON file to `state_root/merged_verdicts/<task_id>.json`:

```json
{
  "task_id": "T42",
  "verdict": "approved",
  "consensus_rule": "unanimous",
  "verdicts": {
    "gate-architect": "approved",
    "gate-critic": "approved"
  },
  "dissent": [],
  "ts": "2026-04-13T..."
}
```

**Approval words:** `{"approved", "approve", "pass", "passed"}` — any of these in a verdict counts as approval. Everything else is rejection.

**Consensus rules:**
- `unanimous` — all `fan_in.review.required` must approve
- `majority` — strict majority: `approve_count > total / 2`. For 2 reviewers, both must approve (1 > 1.0 is false). Ties = rejection.
- `any_pass` — at least one approval

**Fan-in safety:** `trackers.pop(request_id)` must ONLY fire AFTER successful verdict write. If verdict write fails, the tracker is preserved for recovery. Otherwise the fan-in is "complete" but no verdict exists — check_gate blocks the commit indefinitely with no recovery path except manual JSON creation.

**Single writer:** Only the watcher writes to `merged_verdicts/`. check_gate reads. `orch override` writes as emergency path only.

---

## DELIVERED state detection

DELIVERED triggers when the coder has a **done marker** in outbox (file with `done_` prefix) AND no `merged_verdicts/<task_id>.json` exists yet.

**Critical:** DELIVERED must filter for `done_` prefix markers only, NOT any outbox file. A `review_request` in the outbox is NOT a done marker — triggering DELIVERED on any outbox file would falsely lock the coder before they've finished work.

**Race condition warning:** The watcher's main loop moves outbox files to archive after processing. If the watcher runs before dispatch-gate fires, the done marker may already be archived → agent falls to WAITING instead of DELIVERED. **Implemented detection:** check for an active fan-in tracker for the agent's task (in `trackers.json`) rather than outbox file presence. Tracker persists from review_request fan-out until `trackers.pop()` after successful verdict write.

**Git commit detection in DELIVERED:** Use `shlex.split()` for robust command parsing, not substring match. `"git commit" in command` would match `echo "git commit"` — `shlex` parses properly.

---

## Work branch model

Commits to **work branches** are ungated — every intermediate commit is a safety checkpoint. Gate fires only on merge to protected branch.

Config: `gate.protected_branches: ["dev", "main"]`. Commits to any other branch pass ungated.

---

## Approval override / escape hatch

`orch override <task_id>` writes force-approval to merged_verdicts with `"override": true, "by": "allan"`. Audit log records it. Not routine — disaster recovery only.

---

## Wake + injection mechanism

Allan already has this working for voice notes. The orchestrator reuses the same plumbing.

**Coder → Monitor:** PostToolUse hook → JSON summary → monitor inbox → tmux wake → UserPromptSubmit hook → additionalContext → monitor judges.

**Monitor → Coder halt:** `flag_file` (default, instant block) or `inbox_inject` (latency depends on wake).

**Wake gotcha:** `tmux send-keys ENTER` may send empty submission. Workaround: single space + Enter.

---

## Watcher — four jobs

**COPY:** Fan-out per `config.routing`. N recipients driven by list length.
**MERGE:** Fan-in per `config.gate.consensus_rule` (unanimous/majority/any_pass). Timeout → escalate.
**DISTRIBUTE:** Route by `TO:` header + CC rules.
**LIVENESS:** Separate ticker, re-wakes idle agents. Never blocks main loop. POC: inactivity wake only.

---

## Coder workflow

1. Boot → ready file → WAITING (Read only)
2. Task arrives in inbox → WORKING (all tools)
3. Execute on work branch (ungated commits). Monitor receives live stream.
4. Deliver → done marker + diff + review_request → DELIVERED (only `git commit` allowed)
5. Reviewers judge → watcher merges verdicts
6. Gate passes → merge to protected branch
7. Task advances → WAITING

---

## Coexistence with Allan's permission hooks

Two independent systems in one `settings.local.json`. Both fire for each event. Independent decisions. If EITHER blocks (exit 2), action is blocked.

**Orchestrator hooks must NOT:**
- Read or write `roles.json` (Allan's config)
- Call functions from `common.ps1` (Allan's PS helpers)
- Register PermissionRequest hooks (Allan's auto-approve handles that)
- Check folder access (Allan's pre-tool-guard handles that)
- Touch `~/.claude/pressure/*` (Allan's state directory)

**Orchestrator hooks CAN:**
- Read `GATE_AGENT_NAME` from env
- Read/write `.orchestrator/` and `dispatch/`
- Block via exit 2 (independent of Allan's hooks)
- Inject context via `additionalContext` (both systems can inject; Claude Code merges)

---

## Hook script template (standard)

```python
#!/usr/bin/env python3
"""<name>.py — <one-line description>
Event: PreToolUse | PostToolUse
Matcher: Bash | Write|Edit|MultiEdit | *
"""
import json, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lib.common import hook_input, resolve_path, audit_log

def main():
    data = hook_input()
    agent = os.environ.get('GATE_AGENT_NAME', '')
    if not agent:
        return  # P3: opt-in — inert without identity
    tool = data.get('tool_name', '')
    if tool not in RELEVANT_TOOLS:
        return  # early exit
    # --- logic ---

if __name__ == '__main__':
    try:
        main()
    except Exception:
        # P4: fail-secure for enforcement
        print("BLOCKED: Hook error — blocked for safety", file=sys.stderr)
        sys.exit(2)
        # For advisory hooks: sys.exit(0) instead
```

---

## Performance budget

| Component | Budget |
|---|---|
| Process spawn (Python) | ~30ms |
| Config load + parse | ~10ms |
| Identity check (env var) | <1ms |
| Decision logic | <5ms |
| Audit log write | <2ms |
| **Total per tool call** | **<50ms** |

Rules: Use matchers (don't match `*` if only `Bash` matters). Use `if` conditions aggressively. Exit early. Never network I/O. Never read large files. No caching between calls (each is a fresh process). Bash is 33.5% of all tool calls — any per-call overhead is multiplied by volume.

---

## Testing requirements

For each hook, test at minimum:
1. **Allow case** — verify exit 0 AND correct stdout
2. **Block case** — verify exit 2 AND stderr contains reason
3. **Edge case** — malformed input, missing config, unknown agent
4. **Output content** — not just exit codes. "Exit 0 with empty stdout" ≠ "exit 0 with additionalContext"

Test as subprocess (same as Claude Code executes), not by importing the module.

---

## Anti-patterns (don't repeat)

- **Deep config navigation** — use flat config or validated accessor with defaults
- **Substring path matching** — `.Contains("orchestrator/")` hit `docs_orchestrador/`. Use prefix match or regex `(^|/)name/`
- **Glob patterns in config** — config path matchers don't glob-expand; silently fails
- **JSON round-trip data loss** — `read-modify-write` reorders keys. Use atomic writes.
- **Testing exit codes only** — every silent-failure bug would have been caught by asserting output content
- **Launcher trap** — keep CLI thin (<200 lines per command). Engine is not a launcher.
- **Carrying dead features** — before porting from a prior version: "does Allan actually use this?"

---

## Sprint initialization (Component 21)

PowerShell launcher. Round 1 minimum:
1. Validate config
2. Ensure dispatch folders exist
3. Install hooks (merge into existing settings.local.json)
4. Start watcher
5. Launch agent terminals
6. Verify ready files within timeout
7. Load plan into state_root/plans/
8. Dispatch first task

---

## Config shape

```json
{
  "project": "advert",
  "shared_roots": {
    "orchestrator_primary": "W:/Claude_Library/orchestrator",
    "orchestrator_fallback": "D:/IA/orchestrator",
    "agents_primary": "W:/Claude_Library/agents",
    "agents_fallback": "D:/IA/agents"
  },
  "paths": {
    "state_root": ".orchestrator",
    "dispatch_root": "dispatch",
    "plans": ".orchestrator/plans",
    "tasks": ".orchestrator/tasks",
    "current_task": ".orchestrator/tasks/current_task.json",
    "trackers": ".orchestrator/trackers.json",
    "diffs": ".orchestrator/diffs",
    "logs": ".orchestrator/logs",
    "merged_verdicts": ".orchestrator/merged_verdicts",
    "halts": ".orchestrator/halts",
    "runtime_flags": ".orchestrator/runtime_flags",
    "approvals_source": "outbox",
    "halt_mode": "flag_file",
    "playwright_tests": "tests/e2e"
  },
  "wake": {
    "mechanism": "tmux",
    "first_attempt_seconds": 2,
    "retry_interval_seconds": 30,
    "max_retries": 5,
    "monitor_pulse_seconds": 10,
    "idle_threshold_seconds": 120,
    "liveness_check_interval_seconds": 30
  },
  "session": {
    "require_ready_files": true,
    "halt_between_batches": true
  },
  "agents": [
    { "name": "gate-ralph", "profile": "gate-ralph", "executor": true, "roles": ["coder"] },
    { "name": "gate-monitor", "profile": "gate-monitor", "executor": false, "roles": ["monitor", "playwright"] },
    { "name": "gate-architect", "profile": "gate-architect", "executor": false, "roles": ["reviewer"] },
    { "name": "gate-critic", "profile": "gate-critic", "executor": false, "roles": ["reviewer"] }
  ],
  "routing": {
    "cc_all": ["gate-monitor"],
    "review_requests_to": ["gate-architect", "gate-critic"],
    "escalation_target": "allan",
    "on_batch_complete": ["gate-playwright"],
    "on_test_failure": ["gate-ralph"],
    "on_test_passed": ["gate-ralph"],
    "on_stop": ["gate-architect", "gate-critic", "gate-monitor"]
  },
  "gate": {
    "require_approvals_from": ["gate-architect", "gate-critic"],
    "consensus_rule": "unanimous",
    "max_rework_rounds": 3,
    "protected_branches": ["dev", "main"]
  },
  "fan_in": {
    "review": {
      "required": ["gate-architect", "gate-critic"],
      "timeout_seconds": 1200,
      "on_timeout": "escalate_allan"
    }
  }
}
```

Every path configurable. Every count is a list length. Every role is a string.

---

## Hook deployment checklist

Before deploying any new hook:
- [ ] Exits 0 immediately when `GATE_AGENT_NAME` not set (P3)
- [ ] Per-tool hooks in `settings.local.json`, lifecycle in `settings.json` (2.1)
- [ ] Matcher set to narrowest scope
- [ ] `if` condition set where possible
- [ ] Fail-secure for enforcement, fail-open for advisory (P4)
- [ ] No hardcoded names, paths, or composition
- [ ] Atomic writes for state files (P7)
- [ ] Windows-safe paths (pathlib)
- [ ] Tested: allow, block, malformed input, missing config
- [ ] Output content verified (not just exit codes)
- [ ] Decision trace logging
- [ ] Config validated (unknown keys rejected)
- [ ] No overlap with Allan's hooks (no roles.json, no common.ps1, no PermissionRequest, no pressure/*)
- [ ] Under 200 lines
- [ ] Stdlib only

---

## Out of scope (deferred, not trashed)

| Item | Status |
|---|---|
| SQLite state backend | JSON works for POC |
| Full rollback / history tree | `orch resume` covers stuck-task recovery |
| Rich tasks beyond deps+assignee | Explicit scope limit |
| Multi-sprint management | One at a time |
| Dry-run mode | Test live |
| Filesystem events (watchdog) | Polling works for POC. Build later. |
| External integrations (GitHub/Linear/Telegram) | Later |
| Full planner agent | Round 1 = format validator only |
| Anti-lies validator (ENG-9) | After POC |
| Full smoke suite (ENG-12) | 2 real scenarios. Rest later. |
| Pip packaging | Folder on NAS |
| MCP wiring | Round 2+. Code stays, untouched. |
| Queue status CLI (1.2) | KEEP — later |
| Operator controls — pause/resume/drain (1.1) | KEEP — later |
| Rollback/reopen (1.3) | KEEP — later |
| Agent handoff protocol (1.6) | DEFER |
| Combined hook dispatcher (6.8) | BUILD when hook spawn cost measurable |
| Hook result caching (6.9) | Later |
| Regex matcher cleanup (6.10) | Later |
| Versioning + upgrade path (3.6) | BUILD after POC |
| One-shot hook installer full (ENG-10) | After POC |
| Self-test after install (3.4) | BUILD |
| Uninstall/teardown (3.5) | DEFER |
| Write-side access guard | Track — coder can write to other agents' inboxes |
| `resolve_paths()` caller migration | Progressive — 12 callers remaining |
| `common.py` dual resolver unification | After caller migration |
| `routing.escalation_target` required | Make required in schema, remove `"allan"` fallback — validator catches missing config |
| DELIVERED detection via fan-in tracker | DONE in Wave 3 B3 — tracker-based, not outbox file presence |

---

## FLAG: TBDs

| # | Question | Default | Status |
|---|---|---|---|
| F1 | Monitor halt mechanism | `flag_file` | Locked |
| F2 | Role file name | `role_prompt.md` | Locked |
| F3 | Task file format | JSON | Locked |
| F4 | Audit log rotation | Per-sprint + nothing deleted | Locked |
| F5 | Coder completion signal | Commit tag + done marker + DELIVERED state | Locked |
| F6 | Max rework rounds | 3 | Locked |
| F7a | Reviewer capability ceiling | Read: own inbox, diffs (exception), specs, project source. Write: own outbox. | **TBD** |
| F7b | Monitor capability ceiling | + logs read + halt write + Playwright execute | **TBD** |
| F8 | Who writes plans? | Allan for round 1 | Locked |
| F9 | Trigger folder watcher | Not in round 1 | **TBD** |
| F10 | Wake backend alternative | tmux, config ready for swap | Locked |
| F11 | Subagent hook bypass scope | Bypass read guards, write guards stay | **TBD — hookmaster** |
| F12 | Hook `if` field capabilities | Confirmed: permission-rule syntax. Can match `Bash(git commit *)`. | Locked |
| F13 | Cross-directory path resolution | Must work across W:\, D:\, E:\, .worktrees\. `CLAUDE_PROJECT_DIR` is empty. | **SHOW-STOPPER — hookmaster** |

---

## Verification

1. `orch doctor` → all green
2. `orch validate` → PASS. Break config → FAIL with clear error.
3. `orch install-hooks --all` → correct hooks per agent, merged with Allan's hooks
4. `orch status` → shows task, inbox counts, who we're waiting on
5. Sprint launcher initializes cleanly
6. Coder executes on work branch. Monitor halts work. Reviewer fan-out works.
7. Consensus met → merge to protected branch passes gate.
8. Real bug fix e2e through the gate.
9. **Experiment-rig proof:** add 3rd reviewer + change consensus to majority. Zero code changes.
10. `orch resume` recovers stuck task.
11. `orch override` force-approves stuck gate. Audit log records it.

---

## Rejected features (DELETE — will not be built)

These were considered and explicitly rejected by Allan. Do not re-propose, do not implement, do not add back.

| Feature | Why rejected |
|---|---|
| PII / secret scanning in messages | Over-engineering for single-user private repo |
| Max message size enforcement | Over-engineering |
| Rate limiting | Over-engineering |
| Sandbox / test mode | Over-engineering — test live |
| Signed approvals / HMAC | Single-user single-machine. Task_id + diff_sha256 enough. |
| Diff hash binding (enforced) | Supported optionally, not required as policy |
| Secret redaction in delivery | Over-engineering — activity logs have basic redaction, not expanding |
| Web UI | Premature |

These are permanent NO decisions, not deferred. They differ from the "Out of scope" table above which lists items that are deferred (may come back later) vs deleted (will not).

---

**End of master spec v2.4.**

21 components. 32 hard rules. 13 FLAGs (8 locked, 5 TBD including 1 show-stopper). Merged verdict contract. DELIVERED detection rule. Fan-in safety. Hook engineering principles. Performance budget. Testing requirements. Anti-patterns. Coexistence rules. Review insights from 5 critic runs + 4 remediation rounds + Wave 2/3 reviews folded in. Experiment rig — not a product.
