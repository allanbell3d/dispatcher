# Hook System Guide — Specification for Building Hooks

**Owner:** Allan  
**Written by:** Hook Master (Opus 4.6)  
**Date:** 2026-04-12  
**Sources:** v3 live hooks (3.2), v4 proposal (rev07), 4 QA rounds, 76KB of session notes, 14 reference docs  
**Scope:** Any project building Claude Code hooks — orchestrator, dispatch engine, or otherwise  
**Status:** Living document

---

## Purpose

This document captures everything learned from 3 months of building, breaking, and fixing Claude Code hooks across v1 through v4. It exists so the orchestrator project (and any future hook-building project) doesn't repeat the same mistakes.

**Critical distinction:** The orchestrator builds its OWN independent hook scripts. It does NOT merge into Allan's existing permission hooks (pre-tool-guard.ps1, auto-approve.ps1, etc.). The two systems coexist — orchestrator hooks handle dispatch gating, commit gating, and monitor ingest; Allan's hooks handle role-based permissions, folder access, and auto-approve. They share `common.ps1` helpers where useful, but are separate scripts registered as separate hook entries.

---

## Part 1 — Principles

These are non-negotiable. Every design decision must trace to one of these.

### P1. Explicit Identity Over Detection

**Wrong (v3):** Role detected by watching which `memory/<folder>/notes.md` an agent reads first. First read wins, never overwritten. Multi-folder roles hijacked detection. Unknown role had partial restrictions.

**Right (v4):** Identity set explicitly at session creation via `$env:CLAUDE_AGENT_ROLE` (or `GATE_AGENT_NAME` for orchestrator). Priority: env var > identity file > memory-read fallback (logged as degraded).

**For orchestrator:** Use `$env:GATE_AGENT_NAME` set by the launcher/watcher. Never detect identity by file-read patterns.

### P2. Separate Authorization from Approval

**Wrong (v3):** Both `pre-tool-guard.ps1` and `auto-approve.ps1` independently evaluate `Get-FolderAccess`. A fix in one doesn't fix the other. The compound failure of `auto_approve.Bash: "prompt"` + `override: "auto-approve"` silently approved `rm -f` because the approval layer reinterpreted "prompt" as "allow."

**Right:** Authorization ("is this role permitted?") and approval ("should this permitted action skip the user prompt?") are separate questions answered by separate code paths. Never check folder access in the approval hook.

**For orchestrator:** Dispatch-gate and commit-gate are authorization (PreToolUse, exit 2 = block). They don't touch PermissionRequest. Allan's auto-approve hook handles prompt behavior.

### P3. Opt-In Activation

**Wrong (v4 first deploy):** Unknown role hard-blocked Bash in sessions started without the launcher. Allan rolled back to v3 immediately.

**Right (v4 fix):** Every hook begins with:
```python
if not os.environ.get('GATE_AGENT_NAME'):
    sys.exit(0)  # Not a gated session — inert
```

**For orchestrator:** If `GATE_AGENT_NAME` is not set, all orchestrator hooks exit 0 immediately. Zero interference with normal Claude Code sessions.

### P4. Fail-Secure for Enforcement, Fail-Open for Advisory

**Rule:** If a hook enforces security (commit gate, dispatch gate, access guard), malformed config or parse error = BLOCK ALL. If a hook provides advisory info (context injection, monitoring, logging), error = skip silently.

**Wrong:** `pre-tool-guard.ps1` had a bare `exit 0` in the outer catch block — a crash in any security check silently allowed the action. Fail-open for enforcement is a security hole.

**For orchestrator:** Commit-gate and dispatch-gate: wrap in try/catch, catch block = exit 2 with "gate error — blocked for safety." Monitor-ingest and context injection: catch block = exit 0 (don't block the coder because logging broke).

### P5. No Hardcoded Names, Paths, or Composition

**Wrong (v3):** `check_gate.py:65` hardcoded `"dispatch/ralph/outbox/"`. `stop_notify.py:20` hardcoded `recipients = ["monitor"]`. `post-tool-handler.ps1` had 6 agent names in injection messages. `session-lifecycle.ps1` counted bugs-active.md entries (MMA-specific, fired globally).

**Right:** All agent names from `config.agents[]`. All paths from `config.paths.*`. All routing from `config.routing.*`. If the literal string `"ralph"` or `"architect"` appears in engine source, it's a bug.

### P6. Single Writer Per File

**Wrong:** v3 watcher, MCP server, and on_file_message hook all consumed files from `dispatch/*/active/` — triple consumer with no locking. Race conditions lost messages.

**Right (v4):** Each file type has exactly one canonical writer. No merge logic, no locks:
- `trackers.json` — watcher only
- `dispatch/<agent>/inbox/*` — watcher only (fan-out copies)
- `dispatch/<agent>/outbox/*` — owning agent only
- `merged_verdicts/<task_id>.json` — watcher only (fan-in result)
- `audit.log` — `audit_log()` helper only (O_APPEND for concurrent-safe append)

### P7. Atomic Writes for All State Files

**Wrong (v3):** `ConvertTo-Json | Set-Content` on roles.json — a crash mid-write corrupts the entire config. Sprint ON/OFF toggle caused data loss via JSON round-trip key reordering.

**Right (v4):** All state writes use tmp-file-and-rename:
```python
def atomic_write(path, content):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(content)
    os.replace(str(tmp), str(path))  # atomic on same filesystem
```

### P8. Windows-Safe Paths

**Rule:** `pathlib.Path` in Python, `Join-Path` in PowerShell. No hardcoded `/` or `\`. No drive-letter assumptions. Forward slashes work everywhere on Windows via pathlib.

**Wrong:** `normalizedPath.Contains("orchestrator/")` — substring match hit `docs_orchestrador/` (different word). Use regex `(^|/)orchestrator/` or prefix-match with `Test-PathMatch`.

---

## Part 2 — Architecture Rules

### 2.1 Hook Event Placement

**This is load-bearing. Get it wrong and your hook silently never fires.**

| Hook type | Where to register | Why |
|---|---|---|
| Per-tool hooks (PreToolUse, PostToolUse, PermissionRequest) | `<project>/.claude/settings.local.json` | Claude Code only fires project-level per-tool hooks for project tool calls. Global `settings.json` per-tool hooks do NOT fire for project actions. Discovered the hard way in session-10. |
| Lifecycle hooks (SessionStart, Stop, PreCompact, PostCompact, UserPromptSubmit, WorktreeCreate) | `~/.claude/settings.json` (global) | These fire regardless of project context. |

**For orchestrator:** All dispatch-gate, commit-gate, inbox-access-guard, and monitor-ingest hooks go in the PROJECT's `settings.local.json`. Watcher liveness pings (if hook-based) go in global.

### 2.2 One Script Per Event Per System

Allan's permission system: ONE `pre-tool-guard.ps1` for all PreToolUse. ONE `auto-approve.ps1` for all PermissionRequest.

Orchestrator system: ONE `dispatch_gate.py` for all orchestrator PreToolUse. ONE `monitor_ingest.py` for all orchestrator PostToolUse.

**Two separate hook entries in `settings.local.json` for the same event are fine** — Claude Code runs ALL registered hooks for an event. Allan's permission hook runs first (or second — order isn't guaranteed), orchestrator hook runs separately. They're independent subprocesses.

**Use matchers to limit scope:**
```json
{
  "hooks": [{
    "type": "command",
    "command": "python dispatch_gate.py",
    "matcher": "Write|Edit|MultiEdit|Bash"
  }]
}
```

Don't match `*` if you only care about specific tools. Every non-matching call avoids a process spawn.

### 2.3 Use `if` Conditions for Zero-Cost Filtering

Claude Code hook entries support `if:` for tool-pattern matching BEFORE spawning the hook process. From Claude Code source (`schemas/hooks.ts`): uses permission-rule syntax (e.g., `Bash(git *)`). If the condition doesn't match, the hook subprocess is never created — zero cost.

```json
{
  "hooks": [{
    "type": "command",
    "command": "python check_gate.py",
    "matcher": "Bash",
    "if": "Bash(git commit *)"
  }]
}
```

This means `check_gate.py` only fires when the Bash command starts with `git commit`. All other Bash calls (ls, grep, python, etc.) skip it entirely. Use this aggressively.

### 2.4 Python for Engine Hooks, PowerShell for Permission Hooks

| Language | Startup cost | Use for |
|---|---|---|
| Python | ~30ms | Orchestrator engine hooks (dispatch gate, commit gate, monitor ingest, inbox guard) |
| PowerShell 7 | ~80ms | Allan's permission hooks (role detection, folder access, auto-approve) |

**Rule:** Orchestrator hooks are Python. They import from `lib/common.py` (the engine's shared library), not from `common.ps1` (Allan's hooks). The two systems share no code at runtime.

### 2.5 Hook Input/Output Contract

**Input** (JSON on stdin, every hook):
```json
{
  "session_id": "uuid",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "git commit -m 'fix'" },
  "cwd": "/path/to/project",
  "transcript_path": "..."
}
```

**Output to block** (stderr + exit 2):
```
BLOCKED: Commit gate — no approval for task T42
```

**Output to inject context** (stdout JSON + exit 0):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "string injected into agent's next turn"
  }
}
```

**Output for PermissionRequest** (stdout JSON + exit 0):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": { "behavior": "allow" }
  }
}
```

**CRITICAL:** PermissionRequest output requires `hookSpecificOutput.decision.behavior`, NOT `permissionDecision`. The entire v4 auto-approval engine was non-functional until this format bug was caught in QA (F-01). `permissionDecision` is a PreToolUse-only key and is silently ignored in PermissionRequest.

### 2.6 Subagent Detection

Check for `transcript_path` in hook input — present for subagents, absent for main sessions. This is a Claude Code structural guarantee.

```python
is_subagent = bool(data.get('transcript_path'))
```

**Orchestrator design choice:** Subagents spawned by a gated coder inherit the coder's dispatch state. They are NOT independent agents. The dispatch-gate hook reads `GATE_AGENT_NAME` (set on the parent session), and subagents inherit the parent's env.

---

## Part 3 — Anti-Patterns (Don't Repeat These)

### 3.1 Deep Config Navigation

**The single most common bug class in v4 build.** Three variants:
- Wrong tree depth: `resolvedRole.injection.triggers` vs `resolvedRole.triggers` (one level off)
- Wrong key name: `compaction_survival_rules` vs `compaction_reinjection_rules`
- Wrong source object: reading from `knowledge_capture` when value is at `paths.knowledge_store`

**Fix:** Flat config. If you must nest, provide a validated accessor:
```python
def config_get(config, *keys, default=None):
    """Navigate nested config safely. Returns default on any miss."""
    cur = config
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
```

### 3.2 Testing Exit Codes Instead of Output

**v4 QA lesson:** Auth/approval tests verified exit codes. Lifecycle tests checked "did it crash?" Every silent-failure bug (F-02 through F-07) would have been caught by asserting on output content.

**Rule:** For enforcement hooks, test THREE things: (1) exit code, (2) stderr content (block message), (3) stdout content (JSON output). "Exit 0 with empty stdout" and "exit 0 with correct JSON" are different.

### 3.3 Substring Path Matching

**Bug:** `.Contains("orchestrator/")` matched `docs_orchestrador/`. `.Contains("docs/")` could match `mydocs/`.

**Fix:** Use prefix match with trailing-slash semantics (StartsWith) or regex `(^|/)name/`. Never use `.Contains()` for path matching.

### 3.4 Glob Patterns in Config

**Bug:** Config had `"dispatch_pattern": "dispatch/*/active/"` but the path matcher does prefix or exact matching, not glob expansion. `dispatch/sonnet/active/task.md` did NOT match. Dispatch write protection was dead.

**Fix:** If config supports patterns, implement actual glob matching. If not, don't put globs in config — they silently fail.

### 3.5 PowerShell 7 Null-Conditional Bug

**Bug:** `$obj.PSObject.Properties['key']?.Value` is broken in PS7. All instances had to be replaced with a `Get-Prop` helper.

**Fix:** Never use `?.` on PSObject in PowerShell 7. Use explicit null checks or helper functions. (Not relevant if orchestrator hooks are Python, but worth knowing.)

### 3.6 JSON Round-Trip Data Loss

**Bug:** `ConvertFrom-Json | modify | ConvertTo-Json` reorders keys and can lose data. Allan's `safety_rules` were probably lost this way.

**Fix:** For JSON state files, use atomic writes. For config files that humans also edit, consider preserving key order (Python's `json.dump` preserves insertion order by default). Never read-modify-write the full file if you can patch a specific section.

### 3.7 The Launcher Trap

**Why v4 stalled:** The launcher grew to 119KB / 2,318 lines. Hook management got crammed into it. `manage-roles.ps1 deploy` was incomplete. The modules themselves were solid (130+ tests, 3 QA rounds) but the tooling was unfinished.

**Lesson:** Keep CLI tooling thin. `orch doctor`, `orch install-hooks`, `orch status` — each should be under 200 lines. If a command grows past that, it's doing too much. The orchestrator is NOT a launcher — it's an engine with a thin CLI.

### 3.8 Carrying Dead Features Forward

**v3's main sin:** v1 concepts ported to v2 ported to v3 without rethinking. Features nobody used kept accumulating.

**Rule:** Before implementing a feature from a prior version, ask: "Does Allan actually use this?" If the answer is "it was there before," that's not a reason. Cut it.

---

## Part 4 — Implementation Standards

### 4.1 Hook Script Template (Python)

```python
#!/usr/bin/env python3
"""<name>.py — <one-line description>

Event: PreToolUse | PostToolUse
Matcher: Bash | Write|Edit|MultiEdit | *
"""
import json, os, sys, pathlib

# Add engine lib to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'lib'))
from common import hook_input, resolve_path, audit_log

def main():
    data = hook_input()  # parse stdin JSON
    tool = data.get('tool_name', '')
    agent = os.environ.get('GATE_AGENT_NAME', '')

    # P3: opt-in activation — inert without identity
    if not agent:
        return  # exit 0

    # Early exit for irrelevant tools
    if tool not in ('Bash', 'Write', 'Edit'):
        return

    # --- Your logic here ---

    # To block (enforcement):
    # print("BLOCKED: reason", file=sys.stderr)
    # sys.exit(2)

    # To inject context (advisory):
    # print(json.dumps({"hookSpecificOutput": {
    #     "hookEventName": "PreToolUse",
    #     "additionalContext": "message for agent"
    # }}))

    # To allow (default):
    return  # exit 0

if __name__ == '__main__':
    try:
        main()
    except Exception:
        # P4: fail-secure for enforcement
        print("BLOCKED: Hook error — blocked for safety", file=sys.stderr)
        sys.exit(2)
        # OR for advisory hooks:
        # sys.exit(0)
```

### 4.2 Config Access Pattern

```python
# WRONG — deep navigation, each level can KeyError
webhook_url = config['notification']['channels']['slack']['webhook_url']

# RIGHT — validated accessor with default
webhook_url = config_get(config, 'notification', 'channels', 'slack', 'webhook_url',
                         default=None)
if not webhook_url:
    audit_log('warn', 'slack webhook not configured')
```

### 4.3 State File Writes

```python
# WRONG — crash mid-write corrupts file
with open(tracker_path, 'w') as f:
    json.dump(state, f, indent=2)

# RIGHT — atomic write
def atomic_write(path, content):
    path = pathlib.Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(content, encoding='utf-8')
    os.replace(str(tmp), str(path))

atomic_write(tracker_path, json.dumps(state, indent=2))
```

### 4.4 Logging

One audit log engine, one append function, one log path from config:

```python
def audit_log(event, **fields):
    """Append one JSON line to the audit log. O_APPEND for concurrent safety."""
    log_path = resolve_path('audit_log')
    entry = {
        'ts': datetime.now(tz=timezone.utc).isoformat(),
        'event': event,
        **fields
    }
    line = json.dumps(entry, default=str) + '\n'
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(line)
```

Multiple output files from different sources are fine (per-agent activity, per-toolcall monitor feed, central audit). But they all go through ONE function so the format is consistent and the log path is config-driven.

### 4.5 Decision Tracing

Every hook invocation should produce at least one trace entry. Use a standard format:

```
2026-04-12 03:34:37.962 | CALL  | agent=ralph tool=Bash file=[] | 
2026-04-12 03:34:37.980 | ALLOW | agent=ralph tool=Bash file=[] | bash-pass
2026-04-12 03:34:38.100 | DENY  | agent=ralph tool=Bash file=[] | commit-gate: no approval for T42
```

Log location: configurable via `config.paths.decision_log`. Default: `<state_root>/decision_trace.log`.

---

## Part 5 — Testing Requirements

### 5.1 Minimum Test Coverage

For each hook, test at minimum:
1. **Allow case** — tool call that should pass. Verify exit 0 AND correct stdout (empty or valid JSON).
2. **Block case** — tool call that should be denied. Verify exit 2 AND stderr contains the block reason.
3. **Edge case** — malformed input, missing config, unknown agent. Verify the hook doesn't crash and follows P4 (fail-secure or fail-open as appropriate).
4. **Output content** — not just exit code. "Exit 0 with empty stdout" and "exit 0 with `additionalContext`" are functionally different.

### 5.2 Test Execution Model

Run hooks as subprocesses, same as Claude Code does:
```python
result = subprocess.run(
    ['python', 'hooks/dispatch_gate.py'],
    input=json.dumps(test_input),
    capture_output=True, text=True,
    env={**os.environ, 'GATE_AGENT_NAME': 'ralph'},
    timeout=5
)
assert result.returncode == 0  # or 2 for block
assert 'BLOCKED' not in result.stderr  # or 'in' for block
```

Do NOT import the hook module and call functions directly — that tests different code paths than what Claude Code actually executes.

### 5.3 Config Validation Tests

```python
# Valid config passes
assert validate_config(good_config) == True

# Missing required field fails with field name in error
result = validate_config(config_without_agents)
assert 'agents' in result.error

# Unknown key fails (typos must not silently pass)
result = validate_config(config_with_typo_agenst)
assert result.error  # rejects unknown key 'agenst'
```

---

## Part 6 — Security Rules

### 6.1 Hardcoded Safety Gates

Certain commands are dangerous regardless of role. Block them in PreToolUse BEFORE any role config is consulted:

| Pattern | What it catches |
|---|---|
| `\brm\s+-[a-z]*[rf]` | rm -f, rm -rf |
| `\brm\s+[^-\s\|]` | rm <path> |
| `\brmdir\b` | rmdir |
| `\bremove-item\b` | Remove-Item |
| `\bdel\s+` | del |

These cannot be bypassed by auto-approve, sprint mode, or emergency unlock. Only an explicit `bash_allow_destructive: true` flag on a role overrides them.

### 6.2 Command Injection from Config

**v4 bug (C1):** A `.claude/guard-config.json` in a cloned repository could inject commands via injection triggers with `command` type sources. Project config merged on top of user config = arbitrary code execution.

**Fix:** If config supports command execution (injection sources, health checks), gate it behind an explicit feature flag (default: disabled) that can only be set in the user-level config, not project-level.

### 6.3 Session ID Validation

Session IDs are used to construct file paths. Without validation, path traversal is possible. Validate with:
```python
import re
if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
    raise ValueError("Invalid session ID")
```

### 6.4 Bash Bypass of File Guards

**v3 bug:** `PROTECTED_TOOLS = {Read, Grep, Glob}` but Bash not in the set. `Bash(cat .orchestrator/plans/prd.json)` walked around the inbox-access guard.

**Fix:** For the orchestrator inbox-access guard, include Bash in protected tools. Scan Bash command strings for path patterns matching protected directories. Accept that this is heuristic, not perfect — but it catches the 90% case.

---

## Part 7 — Performance Rules

### 7.1 Cost Budget Per Tool Call

| Component | Budget |
|---|---|
| Process spawn (Python) | ~30ms |
| Config load + parse | ~10ms |
| Identity check (env var) | <1ms |
| Decision logic | <5ms |
| Audit log write | <2ms |
| **Total** | **<50ms** |

### 7.2 Rules

1. **Use matchers.** Don't match `*` if you only care about `Bash`. Every non-matching tool avoids a 30ms process spawn.
2. **Use `if` conditions.** `if: "Bash(git commit *)"` on the commit-gate hook means it ONLY fires for git commits. All other Bash calls: zero cost.
3. **Exit early.** First line after opt-in check: is this tool relevant? No → return.
4. **Never do network I/O.** No HTTP, no DNS, no API calls in synchronous hooks.
5. **Never read large files.** Config (~5KB) and small state files (<1KB). Not source code, not logs.
6. **No caching between calls.** Each invocation is a fresh process. "Cache" = write to a state file, which is fine for rarely-changing data.

### 7.3 Bash Dominance

From measured data: Bash is 33.5% of all tool calls (508/1516 across 5 sessions). Read is 26%, Edit 22%. Any per-call overhead is multiplied by this volume. A commit-gate hook matching `*` instead of `Bash(git commit *)` fires 500+ unnecessary times per session.

---

## Part 8 — Coexistence with Allan's Permission Hooks

### 8.1 Two Systems, One settings.local.json

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "pwsh ... pre-tool-guard.ps1" }]
      },
      {
        "matcher": "Bash",
        "if": "Bash(git commit *)",
        "hooks": [{ "type": "command", "command": "python ... check_gate.py" }]
      },
      {
        "matcher": "Write|Edit|MultiEdit|Bash|Glob|Grep",
        "hooks": [{ "type": "command", "command": "python ... dispatch_gate.py" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "pwsh ... post-tool-handler.ps1" }]
      },
      {
        "matcher": "Bash|Write|Edit|MultiEdit|Read|Grep|Glob",
        "hooks": [{ "type": "command", "command": "python ... monitor_ingest.py" }]
      }
    ]
  }
}
```

Both systems' hooks are registered. Claude Code runs ALL matching hooks for each event. Order is not guaranteed. Each hook makes its own allow/block decision independently. If ANY hook blocks (exit 2), the action is blocked.

### 8.2 No Shared State

Allan's hooks read `roles.json` and `~/.claude/pressure/*`. Orchestrator hooks read `.orchestrator/config.json` and `dispatch/*/`. No overlap. No shared files. No coordination needed.

### 8.3 Identity Mapping

Allan's system stamps roles via `_role.txt` files from memory-folder reads. Orchestrator system uses `GATE_AGENT_NAME` env var. Both can coexist — an agent can be `gate-ralph` in Allan's system and `ralph` in the orchestrator's config. The mapping is in `config.agents[].profile`.

### 8.4 What Orchestrator Hooks Must NOT Do

- Do NOT read or write `roles.json` (Allan's hook config)
- Do NOT call functions from `common.ps1` (Allan's PS helpers)
- Do NOT register PermissionRequest hooks (Allan's auto-approve handles that)
- Do NOT check folder access (Allan's pre-tool-guard handles that)
- Do NOT touch `~/.claude/pressure/*` (Allan's state directory)

### 8.5 What Orchestrator Hooks CAN Do

- Read `GATE_AGENT_NAME` from env (set by the launcher)
- Read `.orchestrator/config.json` (own config)
- Read/write `dispatch/*/` (own dispatch folders)
- Read/write `.orchestrator/` (own state directory)
- Write to `audit.log` (own log)
- Block tool calls via exit 2 (independent of Allan's hooks)
- Inject context via `additionalContext` (both systems can inject; Claude Code merges them)

---

## Part 9 — Deployment

### 9.1 Install Automation

`orch install-hooks --all --project <path>` must:
1. Read `config.agents[]` to know which agents need which hooks
2. Read existing `settings.local.json` and MERGE orchestrator entries (don't overwrite Allan's hooks)
3. Write the merged file atomically
4. Verify: for each agent, the expected hook entries exist

### 9.2 Uninstall

`orch disable` must:
1. Read `settings.local.json`
2. Remove ONLY orchestrator-owned hook entries (identified by command path containing the engine directory)
3. Leave Allan's hooks untouched
4. Write atomically

### 9.3 Worktree Support

When a worktree is created, `worktree-init.ps1` (Allan's hook) copies hook entries to the worktree's `settings.local.json`. The orchestrator installer must also handle worktrees — either by hooking into `WorktreeCreate` or by having `orch install-hooks` scan worktrees.

---

## Part 10 — Deferred Designs (Specified, Not Built)

### 10.1 Feature Toggle System

Per-feature flags in config, checked at the top of each hook section. Disabled = section skipped (~2ms). Hook process still spawns (~30ms). Acceptable trade-off vs splitting into separate scripts (which multiplies process spawns).

### 10.2 Async Hooks

Claude Code PostToolUse entries support `async: true`. The hook runs without blocking the next tool call. Use for: monitor ingest (coder shouldn't wait for logging), audit writes, notifications. NOT for: commit gate, dispatch gate (those must block).

### 10.3 Sprint vs Normal Mode

Config supports two auto-approve columns: `auto_approve` (normal — conservative) and `auto_approve_sprint` (autonomous — broad allow). A global mode toggle switches which column is read. For orchestrator: sprint mode = agents work autonomously within the gate constraints. Normal mode = every action prompts.

---

## Appendix A — Checklist Before Deploying a New Hook

- [ ] Opt-in activation: exits 0 immediately when `GATE_AGENT_NAME` is not set
- [ ] Correct event placement: per-tool hooks in `settings.local.json`, lifecycle in `settings.json`
- [ ] Matcher set to narrowest scope (not `*` if only Bash matters)
- [ ] `if` condition set where possible (e.g., `Bash(git commit *)`)
- [ ] Fail-secure for enforcement hooks, fail-open for advisory
- [ ] No hardcoded agent names, paths, or team composition
- [ ] Atomic writes for all state files
- [ ] Windows-safe paths (pathlib, no hardcoded slashes)
- [ ] Tested with: allow case, block case, malformed input, missing config
- [ ] Output content verified (not just exit codes)
- [ ] Decision trace logging (CALL/ALLOW/DENY with agent, tool, path)
- [ ] Config validated (unknown keys rejected)
- [ ] No overlap with Allan's permission hooks (folder access, auto-approve)
- [ ] Doesn't read/write Allan's config files (roles.json, pressure/*)
- [ ] Under 200 lines per script (if bigger, it's doing too much)
- [ ] Stdlib only (no pip dependencies in engine code)

---

**End of guide.**

Built from: v1→v2→v3 evolution, v4 proposal (rev07), 4 QA rounds (15+23+6 findings), 76KB of session notes, 14 reference documents, and 14 hours of debugging in this session. Every rule traces to a real bug or a real decision.
