# Wave 5 Execution Runbook

This runbook is the operator-facing guide for the first real Wave 5 sprint.
It assumes the live dispatcher contract:

- agent identity is `gate-*`
- current task lives at `.orchestrator/tasks/current_task.json`
- verdict fan-in lives at `.orchestrator/merged_verdicts/`
- watcher and hook traces live under `.orchestrator/logs/`
- mail moves through `dispatch/gate-*/inbox/`, `outbox/`, `reports/`, `done/`, and `archive/`

## Purpose

Wave 5 is not just a smoke test. It is the first end-to-end operator run with:

- a real task batch
- a real reviewer preset
- live dispatch traffic
- monitor visibility
- recorded results

Use this runbook when Allan wants to launch the sprint, watch it progress, recover from a failure, and close it out cleanly.

## Before You Launch

1. Confirm the branch and workspace are the intended sprint workspace.
2. Read the active scenario in `docs_dev/wave5/SCENARIO_DUBIZZLE_BUGFIX_SPRINT.md`.
3. Confirm the go/no-go checklist in `docs_dev/wave5/WAVE5_GO_NO_GO.md` is complete.
4. Confirm the current task pointer is loaded at `.orchestrator/tasks/current_task.json`.
5. Confirm all agent folders exist under `dispatch/gate-*/`.
6. Confirm the watcher can write to `.orchestrator/logs/watcher.log`.
7. Confirm `trace_hook()` can write to `.orchestrator/logs/decision_trace.log`.
8. Confirm `audit_log()` can write to `.orchestrator/audit.log`.
9. Confirm the monitor inbox is reachable at `dispatch/gate-monitor/inbox/`.

Do not launch if any of the above are unclear. Fix the setup first.

## Launch Sequence

1. Start the dispatcher launcher from `bin/orch_launcher.ps1`.
2. Select the Wave 5 sprint profile, if one is provided.
3. Start the watcher.
4. Start the executor session for `gate-ralph`.
5. Start the reviewer sessions for `gate-architect` and `gate-critic`.
6. Start the monitor session for `gate-monitor`.
7. Start the playwright session for `gate-playwright`.
8. Verify that `dispatch/gate-monitor/inbox/` begins receiving traffic.

If the launcher offers a dry-run, use it first. Only switch to a live launch after the dry-run looks correct.

## During The Sprint

Keep the run narrow and controlled.

- Leave `.orchestrator/tasks/current_task.json` alone unless the sprint flow explicitly advances it.
- Do not swap reviewer presets mid-run unless the scenario says to.
- Watch `dispatch/gate-ralph/outbox/` for outgoing work.
- Watch `dispatch/gate-architect/inbox/` and `dispatch/gate-critic/inbox/` for review requests.
- Watch `dispatch/gate-monitor/inbox/` for live activity summaries.
- Watch `.orchestrator/merged_verdicts/` for the commit gate result.
- Watch `.orchestrator/logs/decision_trace.log` for hook decisions.
- Watch `.orchestrator/logs/watcher.log` for watcher delivery and wake behavior.

If a reviewer rejects a change, stop treating it as a surprise. That is the expected rework path.

## Recovery

Use the shortest fix that restores the live flow.

- If a reviewer file never arrived, inspect the sender outbox and the watcher log.
- If the monitor inbox is empty, verify `gate-monitor` is in `cc_all` and that `monitor_ingest.py` is enabled.
- If the commit gate blocks unexpectedly, check `.orchestrator/merged_verdicts/<task_id>.json`.
- If the watcher is alive but stale, check `.orchestrator/runtime_flags/STOP` and the watcher log.
- If a hook is failing, check `.orchestrator/logs/decision_trace.log` before guessing.

Do not clear or rewrite runtime history to hide the problem. Fix the delivery path and rerun the step.

## Closeout

When the sprint ends:

1. Record the observed outcome in `docs_dev/wave5/WAVE5_RESULTS_TEMPLATE.md`.
2. Note the final task ID and verdict state.
3. Capture the commit hash that represents the end state.
4. Record any delivery failures or monitor blind spots.
5. Confirm whether the next batch can reuse the same reviewer preset.

If the sprint was interrupted, close out the interruption state just as carefully as a successful run.
