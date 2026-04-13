# Hook Testing Matrix

Use this matrix before the first real Wave 5 sprint and again if a hook behaves strangely during the run.

## Pre-Tool Hooks

| Hook | Trigger | Expected Outcome | What To Check |
|---|---|---|---|
| `dispatch_gate.py` | Before a tool call | Blocks or allows based on current gate state | Decision trace, current task, inbox state |
| `inbox_access_guard.py` | Before reading dispatch mail | Allows only the right agent to read the right inbox | Decision trace, agent identity, inbox path |
| `check_gate.py` | Before `git commit` | Allows commit only when merged verdict exists and is approved | `.orchestrator/merged_verdicts/<task_id>.json`, decision trace |

## Post-Tool Hooks

| Hook | Trigger | Expected Outcome | What To Check |
|---|---|---|---|
| `monitor_ingest.py` | After coder tool activity | Writes monitor summary into `dispatch/gate-monitor/inbox/` | Monitor inbox, watcher log, `cc_all` |
| `activity_logger.py` | After tool activity | Writes an activity line and optional shipping record | `.orchestrator/logs/activity_<agent>.log`, audit log |
| `dispatch_next_bug.py` | After a successful commit | Advances or closes the current task | `.orchestrator/tasks/current_task.json`, merged verdict archive, decision trace |
| `stop_notify.py` | On stop or halt events | Notifies the routed recipients | Dispatch inboxes, audit log, decision trace |

## File-Changed Hooks

| Hook | Trigger | Expected Outcome | What To Check |
|---|---|---|---|
| `dispatch_next_bug.py` | Successful commit that matches the current task | Advances task state and archives the used verdict | Current task file, merged verdict archive |
| `monitor_ingest.py` | Mail-shaped tool activity from a coder | Delivers a readable summary to `gate-monitor` | `dispatch/gate-monitor/inbox/` |

## Stop And Recovery Hooks

| Hook | Trigger | Expected Outcome | What To Check |
|---|---|---|---|
| `stop_notify.py` | Sprint stop or halt condition | Sends stop awareness to routed recipients | Monitor inbox, reviewer inboxes, audit log |
| `check_gate.py` | Commit attempt with missing approval | Denies commit and explains why | Merged verdict file, current task, decision trace |

## Test Order

1. Run the pre-tool hooks first.
2. Run the post-tool hooks next.
3. Confirm the monitor inbox is receiving live activity.
4. Confirm the commit gate denies an unapproved commit.
5. Confirm the successful-commit path advances the task cleanly.
6. Confirm the stop path sends a visible notification.

## Pass Criteria

- Every hook writes a trace entry when it should.
- Every delivery lands in the correct `dispatch/gate-*` folder.
- The commit gate reads the merged verdict for the current task ID.
- The monitor can see the sprint while it is running.

If a hook fails here, fix it before the real sprint instead of trying to work around it manually.
