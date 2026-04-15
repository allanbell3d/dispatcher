# Orchestrator Launcher — Spec

**Owner:** Allan
**Format:** PowerShell 7 GUI launcher, same pattern as `mma-launcher_v8.ps1`
**UI:** Arrow-key menus (`New-MenuItem` + `Read-ArrowMenu`), breadcrumb nav, back-stack, themes
**Goal:** Single control panel for the full orchestrator lifecycle — designed to merge into mma-launcher as a menu section

---

## Main screen — live status dashboard

The main menu shows live status at the top before any menu items:

```
═══════════════════════════════════════════════════
  ORCHESTRATOR CONTROL PANEL
═══════════════════════════════════════════════════
  Project:    Advert (E:\Business\...\Advert)
  Config:     .orchestrator/config.json ✓
  Watcher:    Running (PID 12345) | uptime 2h 14m
  Agents:     3/4 ready  [ralph ✓] [architect ✓] [critic ✓] [monitor ✗]
  Task:       T03 — "Fix photo upload order"
  Gate:       Waiting on critic (architect approved 2m ago)
  Last event: 14:32:07 — COPY review_request to architect, critic
═══════════════════════════════════════════════════
```

Status refreshes on every menu return. Data sources:
- Watcher: check process by PID file or `Get-Process`
- Agents: check `dispatch/<agent>/ready` file existence
- Task: read `.orchestrator/current_task.json`
- Gate: read `.orchestrator/merged_verdicts/` + `.orchestrator/trackers.json`
- Last event: tail `.orchestrator/logs/audit.log`

---


## Menu structure

```
───── Sprint Control ─────
1. Launch Sprint...             → submenu: configure & launch (Steps 1-4 below)
2. Pause Sprint                 → write halt flags for all coders, watcher keeps running
3. Resume Sprint                → clear halt flags, re-wake all agents
4. Stop Sprint                  → write STOP, clean watcher shutdown, close summary

───── Monitoring ─────
5. Status Dashboard             → live status (same data as main screen header)
6. Sprint Status (full)         → full table: task, inboxes, fan-ins, verdicts, timings
7. View Decision Trace          → spawn PowerShell with `Get-Content -Wait -Tail 50` on decision_trace log
8. View Audit Log               → spawn PowerShell with `Get-Content -Wait -Tail 50` on audit.log

───── Agent Control ─────
9. Open Agent Terminal...       → submenu: pick agent, pick launch mode
10. Attach to Session           → pick agent, attach to existing psmux session
11. Resume Stuck Task...        → pick task, re-dispatch
12. Override Verdict...         → pick task, force-approve, audit logged
13. Clear Halt Flags            → remove all halt flags (different from Resume Sprint — doesn't re-wake)

───── Hook Control ─────
14. Toggle Hook...              → per-hook enable/disable via flag file
15. Hook Status                 → table: each orchestrator hook, enabled/disabled
16. Enable ALL Hooks            → restore all orchestrator hooks to active
17. Disable ALL Hooks           → emergency kill switch, all orchestrator hooks disabled
18. Sprint Mode ON              → patch orchestrator roles in roles.json from sprint_on.json
19. Sprint Mode OFF             → patch orchestrator roles in roles.json from sprint_off.json
20. Folder Unlock...            → toggle folder_overrides.enabled in roles.json

───── Install Options ─────    → submenu:
21. Deploy to Project...        → FolderBrowserDialog: create project structure + write hooks
22. Deploy Engine...            → FolderBrowserDialog: copy engine code to NAS or D:\
23. Delete from Project...      → FolderBrowserDialog: remove orchestrator from project
24. Delete Engine...            → FolderBrowserDialog: remove deployed engine code
25. Backup Settings             → backup roles.json + settings.local.json (timestamped, keep 5)
26. Restore Settings            → pick from available backups to restore

───── Configuration ─────
27. Change Project Directory    → FolderBrowserDialog to pick project root
28. Validate Config             → run orch validate, show results
29. Doctor                      → pre-flight checks, green/red table
30. Reset Watcher State         → clear trackers.json, merged_verdicts/, restart watcher
31. Force Kill Watcher          → kill watcher process immediately

───── Quick Access ─────
32. Audit Log (folder)          → open .orchestrator/logs/ in Explorer
33. Dispatch Folders            → open dispatch/ in Explorer
34. Agent Inboxes...            → pick agent, open dispatch/<agent>/inbox/ in Explorer
35. Config File                 → open .orchestrator/config.json in editor
36. Spec & Plans                → open docs/ in Explorer
37. Open Project Folder         → open project root in Explorer

38. Quit
```

**How Sprint Mode works:**

Two sprint profile files containing ONLY the orchestrator role blocks. Launcher patches them into the live `roles.json` without touching other roles.

```
.orchestrator/sprint_profiles/
├── sprint_on.json      ← orchestrator roles only, sprint permissions
└── sprint_off.json     ← same roles, conservative permissions
```

**Mechanism:**
1. Read live `~/.claude/hooks/roles.json`
2. Read selected profile (`sprint_on.json` or `sprint_off.json`)
3. For each role key in the profile: replace that role's block in live file (`roles.roles.<name>`)
4. Set `hooks_config.sprint_active` and `hooks_config.auto_approve_mode` from the profile
5. Atomic write back to `roles.json` (tmp + rename, not `Set-Content`)

Non-orchestrator roles (hook-master, allan, etc.) are **untouched** — only roles in the profile get patched.

The launcher shows which profile is active by checking `hooks_config.sprint_active` in the live `roles.json`.

**POC scope:** one-button patch. Allan configures both profile files manually. Post-POC: launcher can offer per-role editing within each profile.



---

## Launch Sprint submenu (item 1)

Multi-step wizard with adjustable defaults. Each step shows current selection and allows change.

### Step 1 — Select agents

Show all agents from `config.agents[]` with checkboxes. Default: all selected.

```
Select agents for this sprint (Space to toggle, Enter to confirm):
  [✓] gate-ralph      (coder)      session: gate-ralph
  [✓] gate-architect  (reviewer)   session: gate-architect
  [✓] gate-critic     (reviewer)   session: gate-critic
  [✓] gate-monitor    (monitor)    session: gate-monitor
  [ ] gate-playwright  (tester)    session: gate-playwright
```

Allan can toggle any agent on/off. Session names shown are defaults from `session_prefix + agent.name` but editable in Step 3.

### Step 2 — Select launch mode per agent

For each selected agent, pick how to launch:

```
Launch mode for ralph:
  1. Bare terminal (psmux session only, no AI)
  2. Claude Code (claude)
  3. Claude Code resume (claude --resume)
  4. Claude Code with model (claude --model opus)
  5. Custom command...
  6. Skip (session exists, don't touch it)
```

Default: option 2 for all agents. Allan can set different modes per agent (e.g., ralph=Sonnet, architect=Opus, critic=Opus, monitor=bare).

Allow a **"same for all"** shortcut: if Allan picks a mode for the first agent, offer "Apply to all remaining? (Y/n)".

### Step 3 — Session names (optional)

```
Session names (Enter to keep defaults, or edit):
  gate-ralph:      gate-ralph       [Enter to keep]
  gate-architect:  gate-architect   [Enter to keep]
  gate-critic:     gate-critic      [Enter to keep]
  gate-monitor:    gate-monitor     [Enter to keep]
```

Editable. Used for psmux session names. Defaults from `config.session.session_prefix` + agent name.

### Step 4 — Confirm & launch

```
Sprint configuration:
  Agents:  ralph (claude), architect (claude --model opus), critic (claude), monitor (bare)
  Plan:    .orchestrator/plans/wave4.json (3 tasks)
  Watcher: auto-start with supervisor loop

  [Launch]  [Edit]  [Cancel]
```

### Project & install target selection

Two menu items use Windows `FolderBrowserDialog`:
- **Change Project Directory** — FolderBrowserDialog to pick a different project root. Validates `.orchestrator/config.json` exists. Updates dashboard + all paths. No dialog on launcher start — uses last-used project or cwd by default.

---

## Install Options (submenu)

### Deploy to Project

Opens FolderBrowserDialog to pick target project directory. Then:
1. If no `.orchestrator/config.json` exists → copy default config template
2. Create `.orchestrator/` subdirs: `plans/`, `tasks/`, `diffs/`, `merged_verdicts/`, `halts/`, `runtime_flags/`, `logs/`, `approvals/`
3. Create `dispatch/<agent>/inbox/outbox/reports/done/archive/` for every agent in config
4. Create `sprint_profiles/` with `sprint_on.json` + `sprint_off.json` templates
5. Backup existing `settings.local.json` (timestamped)
6. Write hook entries to `<project>/.claude/settings.local.json` — MERGE (append arrays, preserve existing hooks). Hook paths point to deployed engine location from `config.shared_roots`.
7. Print summary: what was created, what was skipped (already exists), hooks written

**Safety:** `mkdir(parents=True, exist_ok=True)` for all dirs — never overwrites existing files or folders. Existing config, plans, tasks, dispatch messages all preserved.

### Deploy Engine

Opens FolderBrowserDialog to pick target directory (NAS `W:\Claude_Library\orchestrator\` or fallback `D:\IA\orchestrator\`). Then:
1. Copy engine code: `hooks/`, `lib/`, `scripts/`, `schemas/`, `bin/`, `tests/`, `mcp-server/`, `VERSION`
2. Copy agent profiles: `agents/profiles/`, `agents/protocols/`
3. Skip: `.orchestrator/`, `dispatch/`, `docs/`, `memory/`, `.omc/`, `__pycache__/`, `.git/`
4. Verify: `python -m py_compile` all deployed `.py` files
5. Print summary: files copied, target path, compile result

**Safety:** Overwrites engine files (that's the point — deploy newer code). Never touches project-specific state.

### Delete from Project

Opens FolderBrowserDialog to pick target project. Then:
1. Confirm: "This will remove orchestrator from <project>. Dispatch messages and logs will be deleted. Continue? Y/N"
2. Remove `.orchestrator/` entirely
3. Remove `dispatch/` entirely
4. Remove orchestrator hook entries from `settings.local.json` (leave Allan's hooks)
5. Print summary

### Delete Engine

Opens FolderBrowserDialog to pick target (NAS or D:\). Then:
1. Confirm: "This will delete the deployed engine at <path>. Continue? Y/N"
2. Remove engine code: `hooks/`, `lib/`, `scripts/`, `schemas/`, `bin/`, `tests/`, `mcp-server/`, `VERSION`
3. Leave `agents/` (shared across projects)
4. Print summary

### Backup Settings

- Copy `~/.claude/hooks/roles.json` → `~/.claude/hooks/backups/roles.json.bak.<timestamp>`
- Copy `<project>/.claude/settings.local.json` → `<project>/.claude/backups/settings.local.json.bak.<timestamp>`
- Keep last 5 backups, delete older
- Print: paths of backed up files

### Restore Settings

- Show list of available backups (sorted by timestamp, newest first)
- Pick one → copy back to live location
- Print: what was restored

### Step 4.5 — Backup before modifications

Before installing hooks or patching roles.json:
- Copy `~/.claude/hooks/roles.json` → `~/.claude/hooks/roles.json.bak.<timestamp>`
- Copy `<project>/.claude/settings.local.json` → `<project>/.claude/settings.local.json.bak.<timestamp>`
- Print: "Backed up roles.json and settings.local.json"

If anything goes wrong, restore from backup.

On launch:
1. Validate config
2. Ensure dispatch folders
3. Start watcher (background process with restart loop)
4. For each agent:
   a. Set `$env:GATE_AGENT_NAME = <agent.name>` in the psmux session environment
   b. Create psmux session with that env var exported
   c. Open terminal → run selected command (claude inherits the env)
5. Wait for ready files (with timeout + progress indicator)
6. If plan exists and no current task: dispatch first task
7. Return to main menu with updated status

**Critical — P1 identity:** The launcher is the ONLY place that sets `GATE_AGENT_NAME`. Every orchestrator hook reads this env var to know which agent is running. Without it, hooks exit 0 (P3 opt-in) and the gate is inert. The launcher sets it per-agent BEFORE claude starts, so the entire session inherits the correct identity. No file-read detection, no role-guessing.

```powershell
# Example: launching gate-ralph with identity
psmux new-session -d -s "gate-ralph" -c $ProjectRoot
psmux send-keys -t "gate-ralph" "`$env:GATE_AGENT_NAME = 'ralph'" Enter
psmux send-keys -t "gate-ralph" "claude" Enter
```

---

## Pause Sprint (item 2)

- Write halt flags for all coder agents (via `set_halt(agent, "sprint paused")`)
- Watcher keeps running (still processes fan-ins, still wakes reviewers)
- Coders blocked at next tool call with "sprint paused" message
- Status shows "PAUSED" in dashboard

---

## Resume Sprint (item 3)

- Clear all halt flags
- Re-wake all agents
- Status returns to normal

---

## Stop Sprint (item 4)

- Write `runtime_flags/STOP`
- Watcher sees it, exits cleanly (exit 0)
- Supervisor loop sees exit 0, does NOT restart
- Print sprint summary: tasks completed, tasks remaining, total time, audit log path
- Optionally close agent terminal windows (prompt: "Close agent terminals? Y/n")

---

## Agent Sessions submenu (item 5)

```
Select agent:
  1. gate-ralph      — session: gate-ralph     status: Running (claude active)
  2. gate-architect  — session: gate-architect  status: Ready (idle)
  3. gate-critic     — session: gate-critic     status: No session
  4. gate-monitor    — session: gate-monitor    status: Running (bare terminal)

Launch mode:
  1. Bare terminal
  2. Claude Code
  3. Claude Code resume
  4. Claude Code with model...
  5. Custom command...
```

If session exists: option to attach, restart, or kill+recreate.

---

## Implementation notes

**Must follow mma-launcher patterns:**
- `New-MenuItem` for all menu items
- `Read-ArrowMenu` for selection
- `Build-*Menu` functions return item arrays
- Main loop dispatches on `$result.type`
- `Push-State`/`Go-Back`/`Cur` for navigation
- Theme support (`$THEMES` hashtable)
- Status lines as non-selectable menu items
- Section dividers with `─────`

**Config-driven — no hardcoded values:**
- Agent names from `config.agents[]`
- Session prefix from `config.session.session_prefix`
- All paths from `config.paths`
- Python path from `$env:PYTHON` or system PATH

**Watcher supervisor built into launcher:**
```powershell
function Start-WatcherWithSupervisor {
    while (-not (Test-Path "$runtimeFlags/STOP")) {
        $proc = Start-Process python $watcherScript -PassThru -NoNewWindow
        $proc.WaitForExit()
        if ($proc.ExitCode -eq 0) { break }  # clean stop
        Write-Host "Watcher crashed (exit $($proc.ExitCode)), restarting in 5s..."
        Start-Sleep 5
    }
}
```

Run as a background job or in the watcher's own headless process. NOT in a psmux session.

**Merge path into mma-launcher:**
- Orchestrator launcher = a `Build-OrchestratorMenu` function
- Added to mma-launcher main menu as item 14: "Orchestrator Control Panel"
- Shares `New-MenuItem`, `Read-ArrowMenu`, themes, psmux helpers
- Self-contained: works standalone OR as mma-launcher submenu

---

## What this spec does NOT cover

- Agent role prompts (already in `dispatcher/agents/profiles/`)
- Hook installation internals (already in `install_hooks.py`)
- Watcher internals (already in `watcher.py`)
- Config schema (already in `config_schema.json`)

This spec covers the USER INTERFACE ONLY — how Allan interacts with the system.
