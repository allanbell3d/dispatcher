---
role: Hook Master
assigned: 2026-03-12
session: Hook Master
---

# Hook Master — Claude Code Hooks Knowledge Base

Allan assigned this role on 2026-03-12. This file is my persistent memory for all things hooks in this project.

**Last updated:** 2026-04-13 | session-20 | **Session:** Case-insensitive roles, trace enrichment, launcher review + fixes

---

## SESSION-20 HANDOFF (2026-04-13)

### What happened
1. **Case-insensitive role detection** — `Allan` vs `allan` mismatch in roles.json. Fixed `Load-RolesConfig` in common.ps1 to convert roles hashtable to case-insensitive via `[System.StringComparer]::OrdinalIgnoreCase`. Also added `-ieq` fallback in post-tool-handler P1 detection. **VERIFIED WORKING.**
2. **Trace enrichment** — pre-tool-guard, post-tool-handler, auto-approve now log Bash commands, Grep patterns, and file paths in CALL entries. No more `file=[]` blanks. **VERIFIED in decision_trace.log.**
3. **Sprint profiles** — created `sprint_on.json` + `sprint_off.json` in `dispatcher/.orchestrator/sprint_profiles/` for 4 gate roles.
4. **Launcher fixes** — copied architect's version (2139 lines) from `dispatcher/orchestrator/bin/` to canonical `dispatcher/bin/`. Applied 15+ fixes. Ran architect + critic Opus verification. Fixed their findings. Allan then tested interactively and found 14+ more issues.

### Hook fixes (DONE, WORKING)
- `common.ps1:Load-RolesConfig` — case-insensitive roles hashtable
- `post-tool-handler.ps1` — case-insensitive P1 detection + trace enrichment (Bash cmd, Grep pattern)
- `pre-tool-guard.ps1` — trace enrichment before CALL log
- `auto-approve.ps1` — trace enrichment before CALL log

### Launcher fixes applied (MANY STILL BROKEN — see below)
- Sprint JSON clobber → per-role patching
- selPos returned on all Read-ArrowMenu exits + cursor memory in main loop
- hook_flags → RuntimeFlagsDir/hooks
- Read-CheckboxMenu accepts [array] + $k→$lbl variable collision fixed
- $EngineRoot computed via walk-up for script paths
- Pause Sprint uses executor flag
- STOP flag cleared before watcher
- GATE_AGENT_NAME uses $a (config name) not $session
- $orchArgs not $args (PS automatic variable collision)
- Skip mode continue before psmux session creation
- Spec & Plans path: "docs" not "dispatcher\docs"
- Deploy Agents: $sel.Value.fullPath property access
- install_hooks.py: ROOT parents[1], --all not --merge

### LAUNCHER STILL BROKEN — Allan's interactive testing (14+ issues)
**Repo moving to `D:\IA\dispatcher_repo` — these issues follow the file.**

1. **Project root resolves to Advert, not dispatcher** — walk-up finds wrong `.orchestrator/config.json` or doesn't run from dispatcher/bin/. "No agents configured" because config loaded from wrong location.
2. **ALL Python subprocess calls lack PYTHONPATH** — only `install_hooks.py` was fixed. `validate.py`, `orchestratorctl.py`, every `& $PYTHON_EXE` call gets `ModuleNotFoundError: No module named 'lib.common'`. Need a wrapper function `Invoke-Python` that sets `$env:PYTHONPATH = $EngineRoot` + `Push-Location $EngineRoot` for every call.
3. **Session prefix double-prefixes** — config agents already named `gate-ralph`, `Get-SessionPrefix` returns `gate-`, result = `gate-gate-ralph`. Fix: check if agent name already starts with prefix before prepending.
4. **Flicker from Clear-Host on every keypress** — Read-ArrowMenu's `Render` calls `Clear-Host` on every Up/Down. Reducing Build-MainMenu calls didn't help. Needs differential render (cursor reposition + overwrite) or double-buffer.
5. **No escape from text prompts** — `Prompt-TextValue` with `AllowEmpty:$false` loops forever on Esc. Needs Esc support or empty-string-as-cancel.
6. **Success messages after Python crashes** — "Verdict overridden. Audit logged." prints even when orchestratorctl.py crashed with exit code 1. Need `if ($LASTEXITCODE -ne 0)` guards.
7. **Enable ALL Hooks: no feedback** — screen blank, no visible confirmation.
8. **Deploy to Project didn't install hooks** — install_hooks.py PYTHONPATH issue.
9. **Folder Unlock UI broken** — no folder browser dialog, falls to text prompts.
10. **Doctor passes but doesn't validate JSON** — checks file existence, not content.
11. **Sprint Mode ON: no visual indication** — need clearer feedback.
12. **Terminal doesn't spawn on Launch Sprint** — psmux new-session runs but no visible window opens.

### Reviews saved
- `dispatcher/docs/reviews/LAUNCHER_REVIEW_hook-master_2026-04-13.md` — my initial review
- `dispatcher/docs/reviews/wave4/launcher_architect.md` — architect verification (Opus)
- `dispatcher/docs/reviews/wave4/launcher_critic.md` — critic verification (Opus)
- GPT + Codex reviews — Allan running, results pending

### Key lessons this session
- **NEVER declare done without interactive testing** — DryRun passes ≠ working. Every menu item needs manual click-through.
- **Systemic fixes > line patches** — PYTHONPATH needed a wrapper function, not per-call fixes. Project root needed rethinking, not walk-up tweaks.
- **Don't copy another agent's file and patch it** — either rewrite the broken parts properly or leave it to the original author. Partial patching created a Frankenstein with neither version's assumptions holding.
- **Reviewer verification ≠ user testing** — Opus agents read code and find logic bugs. Allan finds UX bugs (flicker, no escape, no feedback) that code review can't catch.

### Files changed this session
- `C:\Users\Allan\.claude\hooks\common.ps1` — case-insensitive roles
- `C:\Users\Allan\.claude\hooks\post-tool-handler.ps1` — P1 detection + trace
- `C:\Users\Allan\.claude\hooks\pre-tool-guard.ps1` — trace enrichment
- `C:\Users\Allan\.claude\hooks\auto-approve.ps1` — trace enrichment
- `dispatcher/bin/orch_launcher.ps1` — 15+ fixes (still broken, see above)
- `dispatcher/scripts/install_hooks.py` — ROOT parents[1]
- `dispatcher/.orchestrator/sprint_profiles/sprint_on.json` — created
- `dispatcher/.orchestrator/sprint_profiles/sprint_off.json` — created
- `dispatcher/docs/reviews/LAUNCHER_REVIEW_hook-master_2026-04-13.md` — created

### What's next
1. Wait for GPT + Codex review results
2. Consolidate all reviews into one fix plan
3. Fix the 12 systemic launcher issues properly (wrapper function, project root, prefix logic, flicker)
4. Interactive test EVERY menu item before declaring done
5. Delete diverged copy at `dispatcher/orchestrator/bin/`

---

## SESSION-19 HANDOFF (2026-04-12)

### What happened
Long debugging session (~10hrs Allan time). Gate-architect was blocked from writing to `docs_orchestrador/` and other project folders. Root cause: `CLAUDE_PROJECT_DIR` env var empty in some sessions → `isInsideProject=false` → `outside_project: deny` fired on in-project paths. Fixed `Get-ProjectDir` to fall back to cwd.

Then architect ran `rm -f` and it went through silently because `auto_approve.Bash=prompt` + `override=auto-approve` collapsed to allow. Added hardcoded destructive bash gate that can't be bypassed.

Then Allan wanted: decision trace logging on every tool call, subagent read bypass, write_docs override, hook error spam fix, sprint bypass for orchestrator, launcher v8 with Gate Sprint toggle, and a KISS hook guide for the orchestrator project.

### Late session additions (after initial handoff note)
- **Destructive gate warn-then-allow** — first attempt blocks with coaching questions, exact retry allows. Fixed here-string parse bug (PS `"@` indented inside if block = silent script failure) and undefined `$sessionId` (used `$script:HookSid` instead). `find -delete` pattern added. 31/31 smoke test passing.
- **`docs/` regex tightened** — changed `(^|/)docs/` to `^docs/` so `dispatcher/docs/` and other nested paths aren't caught. Only project-root `docs/` is restricted.
- **critic role fixes** — set `write_docs: true`, `bash_deny_code_files: false`. The `bash_deny_code_files` check lives in `auto-approve.ps1:251` (not pre-tool-guard), was blocking subagent .py writes via PermissionRequest deny.
- **auto-approve.ps1 trace logging** — added CALL/ALLOW/DENY to `decision_trace.log` via `Write-HookDecisionLine`. Both `Approve` and `Deny` functions now log. Previously auto-approve denials were invisible.
- **All hooks now log** — post-tool-handler, session-lifecycle, user-prompt, worktree-init all got `Write-HookEntry` + trace context. Every hook invocation produces at least a CALL row.
- **Log rotation** — `decision_trace.log` moved to `~/.claude/hook-logs/` with 2MB rotation (1 backup kept).
- **C-1 fix (orchestrator)** — extended `inbox_access_guard.py` `_PATH_TOKEN_RE` for Windows backslash paths + deny pathless Bash for stamped agents.
- **Investigated missing Write** — critic's `wave_1_critic.md` allowed by all hooks (trace proves it), no crashes in post-tool-handler. File appeared on retry. Not a hook issue.

### Bugs found late session
- **Here-strings break inside indented blocks** — PS requires `"@` at column 0. Inside an if/else, it's indented → parse error → `$ErrorActionPreference = 'SilentlyContinue'` swallows it → entire script falls through to exit 0 → everything allowed. NEVER use here-strings in hooks. Use `@("line1","line2") -join "\n"` instead.
- **`auto-approve.ps1` `bash_deny_code_files` invisible** — denials from PermissionRequest hook weren't logged anywhere. Agents reported "blocked" but decision_trace showed only ALLOWs. Fixed by adding trace to Approve/Deny functions.
- **Launcher "unlock" didn't unlock everything** — `folder_overrides.enabled=true` only bypassed pre-tool-guard folder access, NOT auto-approve denials. Each hook had independent enforcement. Need unified "unlock means unlock" semantics. Did NOT add emergency-unlock hack to auto-approve — Allan rejected that approach. Real fix: config flags must work correctly when set.

### What was built — v3.2 hooks
All changes documented in `D:/IA/mma-business-assistant/dispatch/hook-master/active/v3.2_hooks/CHANGELOG_v3.2.md`. Summary:

1. **Get-ProjectDir cwd fallback** (common.ps1) — trusts inherited cwd when env var empty
2. **Decision trace logging** (common.ps1) — CALL/ALLOW/DENY to `decision_trace.log`
3. **Destructive bash gate** (pre-tool-guard.ps1) — rm/del/rmdir/shred hard-blocked, `bash_allow_destructive` override
4. **Subagent read bypass** (pre-tool-guard.ps1) — subagents skip folder access for reads
5. **write_docs override** (pre-tool-guard.ps1) — roles with write_docs bypass docs/ read default
6. **Hook error spam fix** (all 3 hooks) — `$ErrorActionPreference = 'SilentlyContinue'` + dot-source inside try
7. **orchestrator/ block removed** (pre-tool-guard.ps1 + roles.json) — was false-matching docs_orchestrador/
8. **Sprint bypass** (pre-tool-guard.ps1) — `sprint_active=true` + `GATE_AGENT_NAME` → skip folder checks, keep safety gates
9. **Launcher v8** (mma-launcher_v8.ps1) — Gate Sprint ON/OFF toggle + status display
10. **HOOK_SYSTEM_GUIDE.md** (docs_orchestrador/) — KISS spec for orchestrator hook building

### Key bugs found this session
- `CLAUDE_PROJECT_DIR` not set in resumed/subprocess sessions → everything treated as outside project
- `auto_approve.Bash: "prompt"` + `override: "auto-approve"` = silent allow (rm -f went through)
- `.Contains("orchestrator/")` substring match hit `docs_orchestrador/` (different word)
- `post-tool-handler.ps1` dot-source outside try block → "hook error" spam on every tool call
- Zero-length stripped folder_access rules silently dropped (project-root rules are dead code, work via fallback)

### Allan's state
- Exhausted, frustrated with 10hrs of debugging instead of building
- Orchestrator refactoring happening in separate architect sessions
- Wants hooks to NOT block the sprint when it runs — Gate Sprint toggle is the answer
- Doesn't want to red-pen docs right now — guide must be self-sufficient

### What's next (NOT session-19 focus — deferred)
1. **First real gated sprint** — will reveal which checks actually conflict. Fix from decision_trace.log data.
2. **hook_trace.log + decision_trace.log rotation** — both growing unbounded
3. **folder_overrides dual semantics** — pre-tool-guard treats enabled=true as global kill switch, Get-FolderAccess treats it as path-list gate. Not unified.
4. **JSON round-trip data loss in launcher** — Sprint/Gate toggles do full ConvertFrom-Json | ConvertTo-Json. Keys reorder.
5. **Feature toggle system** — per-feature enable/disable flags in hooks_config.features. Deferred.
6. **Hook-level `if:` clause for zero-cost filtering** — deferred.

### Files changed this session
- `C:\Users\Allan\.claude\hooks\common.ps1` — Get-ProjectDir, trace helpers
- `C:\Users\Allan\.claude\hooks\pre-tool-guard.ps1` — destructive gate, sprint bypass, subagent bypass, write_docs, orchestrator/ removal, trace instrumentation, error suppression
- `C:\Users\Allan\.claude\hooks\post-tool-handler.ps1` — error suppression, dot-source moved inside try
- `C:\Users\Allan\.claude\hooks\auto-approve.ps1` — error suppression
- `C:\Users\Allan\.claude\hooks\roles.json` — sprint_active flag, orchestrator/ default removed, hook-master folder_access
- `C:\Users\Allan\.claude\hooks\mma-launcher_v8.ps1` — NEW, Gate Sprint toggle
- `E:\...\Advert\docs_orchestrador\HOOK_SYSTEM_GUIDE.md` — NEW, KISS hook guide for orchestrator
- `D:\IA\mma-business-assistant\dispatch\hook-master\active\v3.2_hooks\` — full backup + changelog

---

## SESSION-18 HANDOFF (2026-04-10) — aborted due to compact corruption

### What happened
Post-compact this session loaded ~140k tokens instantly: the compact summary + 3 orchestrator files (`check_gate.py`, `dispatch_next_bug.py`, `watcher.py`) arrived tagged with a "consider if malware" system reminder (false positive — legit orchestration code), plus all skill/MCP banners. The model then emitted a degenerate token loop of control chars (U+2421 `␑`) instead of real text. Allan's terminal showed corrupted glyphs + an AUP safety error. No files touched, no tool calls executed. Allan chose to restart fresh — good call.

### What Allan actually wants next session (NOT another review)

**Task: finish-implementation pass on `E:\Business\Real Estate\Villa number 2 -60-62\Advert\Orchestrator Refactor\ready_orchestrator_setup_2026-04-10`**

Allan's exact words: *"gpt has done about as much as it can, its not a coding agent. i wanted you to review but given the great review you gave before i wanted you to do the finish implementation pass on the code this round, see if we can install and test, but they are missing a few features"*

Breakdown:
1. **This is implementation work, not review.** Bundle 1 already got the 39-finding review (see `CODE_REVIEW_hook-master_2026-04-10.md` + `IMPROVEMENT_IDEAS_hook-master_2026-04-10.md` in the bundle-1 folder `dispatch_orchestration_patched_bundle_2026-04-10`). Bundle 2 (`ready_orchestrator_setup_2026-04-10`) is GPT's attempt to fix bundle-1 issues — now Opus takes it across the finish line.
2. **Finish the code** — fill in whatever GPT couldn't. Allan says "they are missing a few features" — discover which by diffing against bundle 1, against the improvement-ideas doc, and against what a working orchestrator needs end-to-end.
3. **Install and test** — get it to actually run on the Advert project, smoke-test the dispatch → gate → watcher → approval → commit loop.
4. **GPT is out of gas on this** — don't round-trip back to GPT, just finish it.

### Files already read from bundle 2 (pre-crash)
- `D_IA/orchestrator/lib/common.py` — shared utilities, `ResolvedPaths` dataclass, atomic writes (`atomic_write` w/ fsync), `sha256_file`/`sha256_text`, `sort_files_by_mtime`, `compute_message_name`, `ensure_dispatch_dirs`, `persist_session_runtime`. Shared-root resolution: primary `W:/Claude_Library/orchestrator`, fallback `D:/IA/orchestrator`. Has `resolve_project_root` that scans upward for `.orchestrator/config.json`.
- `D_IA/orchestrator/hooks/check_gate.py` — strict task_id match (no filename fallback) + `diff_sha256` binding if approval has one + strict verdict check (approved/pass/passed OR `approved` flag True). **Fixes bundle-1 C2.**
- `D_IA/orchestrator/hooks/dispatch_next_bug.py` — `TASK_TAG_RE = \[task:([A-Za-z0-9._-]+)\]|task:([A-Za-z0-9._-]+)`. Only advances if commit message contains `[task:ID]` matching current task. Archives approvals on success. **Fixes bundle-1 C1.**
- `D_IA/orchestrator/scripts/watcher.py` — persistent trackers via `save_trackers`/`load_trackers` → `runtime_dir/trackers.json`. Uses `sort_files_by_mtime`. Has `require_ready` config gating. Fan-in complete/timeout logic intact. **Fixes bundle-1 C3.**

### Files STILL UNREAD in bundle 2 (read one at a time when needed)
- `D_IA/orchestrator/scripts/doctor.py` — diagnostic/health check (priority — run first during install)
- `D_IA/orchestrator/scripts/install_hooks.py` — hook installer
- `D_IA/orchestrator/scripts/orchestratorctl.py` — CLI
- `D_IA/orchestrator/scripts/render_mcp_config.py` — MCP config generator
- `D_IA/orchestrator/hooks/stop_notify.py` — Stop-event hook
- `D_IA/orchestrator/mcp-server/server.ts` (if it still exists — may have been replaced by hook-only model)
- `D_IA/orchestrator/Project_Template/.orchestrator/config.json` — schema template
- `SETUP.md`, `QUICKSTART.md`, `COMMANDS.md` — docs/contract

### Known gaps to check (bundle-1 findings vs bundle-2)
- **C1** dispatch advances on any git commit → FIXED (TASK_TAG_RE verified)
- **C2** stale approval security hole → FIXED (strict task_id + diff_sha256 verified)
- **C3** fan-in tracker in-memory only → FIXED (trackers.json persistence verified)
- **C4** fast reports race tracker creation → **UNCLEAR** — re-read watcher.py report-handling path with this specific race in mind. Check whether a report arriving BEFORE outbox delivery creates the tracker now falls through to the `direct_targets` branch and gets lost to `done/`.
- **C5** triple consumers of `active/` with no locking → **UNCLEAR** — depends on whether mcp-server still exists. Check render_mcp_config.py and mcp-server/server.ts. If mcp-server is gone → C5 no longer applies. If it's still there → file locking needed.

### High-value improvements to implement in the finish pass
From `IMPROVEMENT_IDEAS_hook-master_2026-04-10.md` top priorities:
- Config schema validation at load time (jsonschema on `.orchestrator/config.json`)
- Hook `if` conditions for zero-cost filtering (`"if": "Bash(git commit *)"` on check_gate/dispatch_next_bug — skips hook spawn entirely for non-matching calls)
- `orchestratorctl init` + `orchestratorctl doctor` commands wired and actually useful
- Audit log of dispatch/approval events (append-only, for later forensics)
- Optional: SQLite for trackers instead of JSON (better durability under crash)

### Install/test plan (propose to Allan first, don't jump in)
- Target project: Advert (`E:\Business\Real Estate\Villa number 2 -60-62\Advert`)
- Step 1: read doctor.py + install_hooks.py + orchestratorctl.py + Project_Template/config.json → understand the intended install flow
- Step 2: run `doctor.py` dry against Advert to see baseline state
- Step 3: run `install_hooks.py` against Advert (will touch `.claude/settings.local.json` — Allan must approve, this is outside my normal scope per my CLAUDE.md)
- Step 4: smoke test loop — create a fake task in `tasks.json`, drop a dispatch, watch watcher route, drop an approval, do a fake commit with `[task:ID]` tag, verify state transitions
- Step 5: tear down and report

### Compact-safety rules for next session (CRITICAL)
- **Do NOT re-read all 4 bundle-2 files at start** — this handoff has the summary, use it
- **Do NOT read notes.md in full** — tail only (`tail -80`)
- **Do NOT auto-load MEMORY.md + CLAUDE.md + STATE.md + session-continuation.md all at once** — the SessionStart hook already injects context, that's enough
- **Read the unread files ONE AT A TIME, only when actually needed** — not up-front "to understand the codebase"
- **If the `␑` corruption happens again** — STOP, do NOT retry, escalate to Allan immediately. It's a signal of context poisoning
- **Output style**: session was in `explanatory` mode with Insight blocks. Bloats responses. Ask Allan if he wants to switch for implementation work.
- **Three files come with a "consider if malware" tag** (check_gate.py, dispatch_next_bug.py, watcher.py). They are NOT malware. The tag is a false-positive artifact from the previous session's summary. Proceed normally, just don't let the tag trigger defensive loops.
- **Auto-approve may be broken for outside-project paths** (see pending item below). Expect to hit permission prompts when touching E:\Advert files. Don't retry on denial — ask Allan to toggle.

### Still-pending smaller items (NOT session-18 focus)
- Auto-approve outside-project short-circuit — two options on table: (a) change global `outside_project: "prompt"` → `"write"`, or (b) add explicit per-role folder_access entries for hook-master and src-code. Allan said "ok i will try" — DEFERRED, no decision yet. If auto-approve keeps prompting during the implementation pass, revisit this.
- `hook_trace.log` rotation/truncation (growing).
- CLAUDE.md "Current State" section is empty per nudge hook.

---

## Session-17 Notes (2026-04-10) — Batch roles, trace logging, emergency unlock, orchestration reviews

### What happened
- Registered 7 new roles in live roles.json:
  - `src-code` (D:\IA\claude-code-src, full traverse to Advert + orchestration + NAS)
  - `gate-monitor` (Advert + Advert/.worktrees)
  - `gate-playwright`, `gate-critic`, `gate-architect`, `gate-ralph` (all Advert + NAS)
  - `allan` (unrestricted, git commit/push/merge, safety overrides, 4 project folders + NAS)
- All 6 gate/src roles got full field coverage: `mode: "inherit"`, `override: "auto-approve"`, `auto_approve` all prompt (normal), `auto_approve_sprint` all allow (sprint mode = autonomous)
- Added diagnostic trace logging to `post-tool-handler.ps1` — writes to `~/.claude/pressure/hook_trace.log`. Covers every decision point in role detection (P1 regex, P2 map fallback, WROTE vs skip vs crash). Wrapped the whole script in try/catch to catch silent failures.
- Fixed the "roles not detected from worktrees" bug — several Advert worktrees had `settings.local.json` but no `hooks` section:
  - `Advert-ralph`, `v2-refactor-phase-b`, `v2-refactor-phase-c`, `v2-refactor-phase-d` had files but NO hooks
  - `Advert-teams`, `v2-refactor-phase-a`, `v2-refactor-phase-c - copia` were missing the file entirely
  - Fixed all 7 worktrees to have the 3-hook wiring (PreToolUse, PostToolUse, PermissionRequest)
  - Also created `D:\IA\orchestration\.claude\settings.local.json` (claude-code-src already had hooks)
- Improved `worktree-init.ps1`: now ensures hooks are present in target settings.local.json even if file already exists (merges hooks section from project root). No more silent hook-less worktrees.
- Changed emergency unlock behavior in `pre-tool-guard.ps1` — previously only bypassed `.claude/` and `secrets/` paths. Now when `folder_overrides.enabled: true`, it exits 0 immediately at the top of the Write block. True kill switch.
- Manually fixed session role files via direct `_role.txt` writes for sessions started before hooks were wired in worktree D (session-continuation first read ambiguity also caused a false `architect` detection for a src-code session — had to correct manually).
- Wrote two long reviews to Advert/Orchestrator Refactor/dispatch_orchestration_patched_bundle_2026-04-10/:
  - `CODE_REVIEW_hook-master_2026-04-10.md` — 39 findings (5 Critical, 9 High, 8 Medium, 10 Low, 7 Architectural). Key findings: C1 (dispatch_next_bug advances on any git commit), C2 (check_gate.py allows stale approvals via filename fallback + null task_id match), C3 (watcher.py fan-in state in-memory only), C4 (fast report races tracker creation), C5 (watcher + hook + MCP all race on active/).
  - `IMPROVEMENT_IDEAS_hook-master_2026-04-10.md` — forward-looking improvements across Functionality, Compatibility, Deployment, Safety, Optimization, Hook optimization. Key insight: Claude Code hooks support `if: "Bash(git commit *)"` permission-rule filter which runs BEFORE spawning the hook process — zero-cost filter for check_gate/dispatch_next_bug.

### Discoveries via claude-code-explorer MCP
- **Hook filter methods** (utils/hooks.ts:1347-1381): matchers use regex if not alphanumeric, pipe-separated exact matches otherwise. `*` or missing = match everything.
- **`if` condition schema** (schemas/hooks.ts): uses permission-rule syntax (e.g., `Bash(git *)`), filters BEFORE spawning. Also supports `once`, `async`, `asyncRewake` flags.
- **PermissionRequest hook output format** (utils/hooks.ts:657-673): EXACTLY this:
  ```json
  {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}
  ```
  Claude Code reads `json.hookSpecificOutput.decision` and assigns to `permissionRequestResult`. Our auto-approve.ps1 Approve function is correct.
- **Built-in HooksConfigMenu** (components/hooks/HooksConfigMenu.tsx): there's a built-in Claude Code UI for managing hooks. Worth exploring as an alternative to the custom launcher.

### Critical bug found in our current system
- **Outside-project folder access defaults to "prompt"**, which in `auto-approve.ps1` line 74 causes `exit 0` BEFORE the per-role auto-approve logic runs. This means hook-master (and any role) gets Claude-native prompts for any file outside the MMA project, regardless of `override: "auto-approve"`.
- **The fix options:**
  1. Change global `outside_project` from `"prompt"` to `"write"` (affects all roles)
  2. Add explicit `folder_access` entries to hook-master for specific paths (surgical)
- Allan chose to "try" one of these — deferred to next session.

### Session-17 bugs Allan found / reported
- Launcher descriptions unclear — "opus_only_files" labeled as "Restrict to coordinator-protected files" is misleading (it's a permission GRANT, not a restriction)
- Sprint/normal mode mapping was initially reversed for the new roles (both set to prompt, should have been normal=prompt / sprint=allow — fixed)
- Roles without `mode`/`override`/`auto_approve_sprint`/`auto_approve_override` silently fall through to default behavior — populated all 4 fields for every new role to prevent this
- Emergency unlock was path-specific, not a global kill switch — fixed

### Key files changed
- `C:\Users\Allan\.claude\hooks\roles.json` — added 7 roles, full field coverage
- `C:\Users\Allan\.claude\hooks\post-tool-handler.ps1` — added Trace-Hook + try/catch wrapper
- `C:\Users\Allan\.claude\hooks\pre-tool-guard.ps1` — emergency unlock = full bypass
- `C:\Users\Allan\.claude\hooks\worktree-init.ps1` — inject hooks into existing settings.local.json
- 7 Advert worktrees' `.claude\settings.local.json` — all now have 3 hooks wired
- `D:\IA\orchestration\.claude\settings.local.json` — created

### Pending for next session
1. **Fix outside-project auto-approve** — decide between global "write" or per-role folder_access entries. Hook-master is currently getting prompted for Advert/orchestration/claude-code-src paths despite `override: "auto-approve"` because the folder_access "prompt" check short-circuits the decision logic.
2. **Trace log cleanup** — hook_trace.log has grown. Consider adding log rotation (truncate if > 100KB) or removing trace once stable.
3. **Allan will ask for hooks design help** — he said he needs to add more hooks to drive the orchestration system. He wants help optimizing them (matcher filters, `if` conditions, once/async/asyncRewake). The improvement doc has section 6 with the blueprint.
4. **C1/C2 critical fixes** for the dispatch orchestration bundle need to be prioritized. Allan has the review file.
5. **ready_orchestrator_setup_2026-04-10** is the improved version of the bundle — already addresses: shared `lib/common.py` with `ResolvedPaths`, shared engine/template separation (D_IA/ vs Project_Template/), SQLite-style atomic writes, sha256 diff binding in check_gate, strict task_id matching (fixes C2 partially), commit-message task-tag extraction (fixes C1), persistent trackers.json, runtime session tracking, doctor.py/install_hooks.py/orchestratorctl.py deployment scripts. Need to review this bundle next session if Allan asks.

### Allan's feedback captured this session
- "opus really overdid itself today" — **sarcasm aimed at a PREVIOUS Opus agent** who built the hooks system and spent 12 hours debugging with many bugs. NOT a critique of my review length. Allan explicitly said: "i dont want you to keep reports brief, i appreciate thorough honest reports". **Action for future sessions:** keep reviews thorough and honest. Don't self-censor to save tokens. Include all findings across all severity levels when doing a code review.
- "its not docs, it cant write claude.md in memory folder" — corrected my initial wrong diagnosis (I thought it was docs/ restriction, it was the opus_only_files filename match)
- "i have emergency unlock on, that was suposed to be there to bypass everything" — Allan expected the launcher toggle to be a true kill switch. My original implementation was surgical (path-matching). Fixed to match his expectation.
- "dont put all auto-aprove let me swith with sprint" — confirmed Allan wants normal=conservative, sprint=autonomous for the new roles. Standard pattern.
- "psmux loads with tmux command" — I was wrong about H4 in the code review. On Windows, psmux registers itself as both names. Corrected verbally.

### Things I did that worked
- Trace logging caught role detection working correctly for gate-ralph (sid=aa3b9bac) and gate-monitor (sid=237ceae3) after hooks were wired in worktree D
- Batch edits with `replace_all: true` on the sprint block worked for flipping all 6 new roles' auto_approve_sprint from prompt to allow in one operation
- Using claude-code-explorer MCP to verify PermissionRequest hook format was the right call — confirmed auto-approve.ps1 format is correct, so the problem is elsewhere (outside-project short-circuit)

### Things to avoid next session
- Don't speculate about root cause — read the actual hook code first. I initially misdiagnosed the "can't write CLAUDE.md" issue as docs/ restriction.
- Don't skip verifying the launcher UI label against actual code behavior — "opus_only_files" label vs actual grant semantics confused Allan.
- Don't misread Allan's tone. "opus overdid itself" was sarcasm about the PREVIOUS Opus agent, not a critique of my work. When in doubt, ask before assuming the feedback is about me.

---

## WHAT HAPPENED

Allan asked for a deep analysis of the v3/v4 hook system to get it working. Three rounds of analysis were done (v3 review, v4 review, architecture options). Allan correctly rejected all three — they proposed architectural restructuring without diagnosing what was actually broken.

A deep-dive trace with 3 parallel lanes found the real problems. Then we spent the session fixing config gaps and discovering code bugs one at a time.

---

## WHAT WAS FIXED THIS SESSION

### Config data restored (roles.json — live + staged)
- `hooks_config.safety_rules` — 8 rules added (hooks_bash_access, settings_bash_access, force_push_main, git_reset_hard, rm_rf_root, drop_database, cd_and_git, compound_ssh). These were missing entirely, causing every safety rule to default to "deny" for all roles.
- `hooks_config.folder_permissions.defaults` — 10 paths added matching pre-tool-guard hardcoded checks. Key name is `"access"` not `"level"` (manage-roles.ps1 reads `entry["access"]`).
- `hooks_config.folder_overrides` + `folder_permissions` structure added to staged (was missing).
- `default_auto_approve` values changed from "allow" to "prompt" (Allan's preference: auto-approve should not be enabled by default).
- 4 orphan roles added: `architect`, `codex-audit`, `ralph`, `skill-master` (memory folders existed with no roles.json entry → null config → silent degradation).
- `opus-boss` role added to staged (was only in live).
- `opus-architect` memory_folders fixed — removed stale `haiku-test` mapping.
- `haiku` memory_folders fixed — changed `haiku-01, haiku-02` to actual folder `haiku-test`.

### Code fixes
- `common.ps1:Get-AutoApproveDecisionV3` — added fallback to `hooks_config.default_auto_approve` when role's auto_approve column is empty. Previously `default_auto_approve` was dead code (the function never read it). Fixed in live + v3.1_hooks + v3_hooks_deployed.
- `pre-tool-guard.ps1` Read section — `"prompt"` folder access was doing `exit 2` (hard block) instead of `exit 0` (delegate to Claude's permission system). The Write section correctly did `exit 0`. Same word, opposite behavior. Fixed in live + v3.1_hooks + v3_hooks_deployed.
- `mma-launcher_v7.ps1` line 119 — source path updated from `staged-hooks` (deleted directory) to `v3.1_hooks`.

---

## WHAT IS STILL BROKEN — DO NOT SUGAR COAT

### v3 is a mess of inconsistencies
The session proved repeatedly that v3 has bugs that can't be found by code review alone. Every time Allan tested something, a new issue surfaced. The "prompt" behavior inconsistency between Read and Write handlers is a symptom — the whole system grew organically with patches on patches. More bugs are guaranteed to exist.

### The destructive JSON round-trip
Sprint ON/OFF and Folder Unlock in the launcher do full `ConvertFrom-Json | modify | ConvertTo-Json` on roles.json. This has been confirmed to reorder keys and potentially lose data. Allan's safety_rules may have been lost this way (or via Install Hooks — root cause still unconfirmed). This pattern is a ticking bomb.

### Folder access system is half-baked
- `outside_project: "prompt"` blocks subagents silently (they can't surface permission prompts)
- `.claude/` deny rule in folder_permissions.defaults matches absolute paths outside the project (e.g. `C:\Users\Allan\.claude\plugins\...`)
- The `Get-FolderAccess` function applies project-relative rules to absolute outside-project paths
- Subagents spawned by agents that had folder_overrides enabled don't inherit the bypass

### default_auto_approve behavior change
The fallback fix means empty `auto_approve: {}` now inherits from `default_auto_approve` (set to "prompt"). Before the fix, empty meant "prompt" anyway (dead code). So behavior is the same FOR NOW. But if anyone changes `default_auto_approve` to "allow" for some tools, all empty roles suddenly get auto-approved. The fix is correct but needs awareness.

### manage-roles presets create broken roles
New roles via manage-roles start with empty `auto_approve: {}`, `safety_overrides: {}`, `folder_access: []`. They depend on global defaults existing — which until today they didn't. Now they do, but the preset should populate from defaults explicitly.

### post-tool-handler.ps1 missing try/catch
Only hook without top-level error suppression. A crash surfaces as a hook error message in Claude's context window, wasting tokens and confusing agents.

### Hardcoded MMA data in hooks
- `post-tool-handler.ps1` has 6 agent names hardcoded in `$agentMemoryMessages`
- `session-lifecycle.ps1` counts bugs-active.md entries and injects MMA-specific rules in the banner
- These only matter for the MMA project but fire globally

### Duplicate Invoke-ContextInjection
Same injection logic copy-pasted in pre-tool-guard.ps1 and post-tool-handler.ps1. Should be one function in common.ps1.

---

## THE REAL QUESTION: V3 PATCHES OR V4 MODULES?

Allan said it himself: "this is exactly the mess v4 was built for, to clean the slate from patches."

The v4 modules (auth-engine, approve-engine, lifecycle-*, etc.) went through 3 QA rounds. All silent failures (F-01 through F-09) were found and fixed. They have consistent behavior by design. They work without the bloated launcher. A thin 3-line dispatcher is sufficient.

v4 stalled because:
1. The launcher grew to 119KB (hook management crammed in)
2. `manage-roles.ps1 deploy` was incomplete
3. Phase 0 (clean slate) was never run

But the MODULES themselves are solid. The question for next session: is it faster to keep patching v3 (whack-a-mole with inconsistencies) or deploy v4 modules with a thin dispatcher and fix the remaining v4 gaps (deploy command, session archival)?

Allan needs to decide. Don't decide for him. Present the evidence honestly.

---

## FILES CHANGED THIS SESSION

### Live (~/.claude/hooks/)
- `roles.json` — safety_rules, folder_permissions, default_auto_approve, 4 new roles, mapping fixes
- `common.ps1` — auto_approve fallback fix
- `pre-tool-guard.ps1` — prompt/read fix
- `mma-launcher_v7.ps1` — source path fix

### Staged (dispatch/hook-master/active/v3.1_hooks/)
- `roles.json` — same as live
- `common.ps1` — same fix
- `pre-tool-guard.ps1` — same fix
- `v3_hooks_analysis_report.md` — NEW (v3 agent report)
- `v4_hooks_analysis_report.md` — NEW (v4 agent report)
- `v3.1_architecture_options.md` — NEW (architect options, now outdated)
- `deep-dive-trace-review-deliverables-working-setup.md` — NEW (trace findings)

### Staged (dispatch/hook-master/active/v3_hooks_deployed/)
- `common.ps1` — same fix
- `pre-tool-guard.ps1` — same fix
- `roles.json` — default_auto_approve fix

---
