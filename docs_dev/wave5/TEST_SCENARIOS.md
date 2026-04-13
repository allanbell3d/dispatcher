# Wave 5 Test Scenarios

These are the scenarios the operator should check during the Wave 5 run. Keep them short and concrete.

## 1. Happy Path

- Load the Dubizzle bugfix batch.
- Start the watcher and all agent sessions.
- Let `gate-ralph` complete one fix.
- Let both reviewers approve.
- Confirm the merged verdict is written.
- Confirm the commit gate allows the commit.
- Confirm the task advances normally.

Expected result:

- `dispatch/gate-monitor/inbox/` receives live summaries
- `.orchestrator/merged_verdicts/<task_id>.json` exists and is approved
- `.orchestrator/tasks/current_task.json` advances only when the sprint rules allow it

## 2. Reviewer Rejection And Rework

- Start the same batch.
- Force one reviewer to reject.
- Confirm `gate-ralph` receives the rejection.
- Confirm the work is revised.
- Confirm the final verdict becomes approved only after rework.

Expected result:

- rejection is visible in the reviewer flow
- rework is visible in the outbox/inbox traffic
- the operator records the rejection and recovery path

## 3. Timeout And Escalation

- Simulate a stalled review or missing response.
- Confirm the watcher keeps the task from silently disappearing.
- Confirm the escalation path is visible to the operator.

Expected result:

- the operator can explain why the task stalled
- the failure is visible in the logs
- no one fabricates a verdict to move the sprint forward

## 4. Monitor Visibility Check

- Send normal coder activity.
- Confirm `gate-monitor` receives an inbox item.
- Confirm the item is readable without opening raw code history.

Expected result:

- monitor inbox traffic is present
- the summary is tied to the current task and tool activity
- the monitor can describe what happened in the run

## 5. Resume Or Override Recovery

- Stop the sprint cleanly.
- Resume from the recorded state.
- If forced, use the operator override path only as a recovery step.

Expected result:

- the operator can tell the difference between resume and override
- override use is recorded in the results template
- the run still leaves a trustworthy audit trail

## Recording Rule

For every scenario, capture:

- what was tried
- what happened
- what failed
- what fixed it
- what should be repeated next time

If the operator cannot explain the failure path, the scenario is not complete.
