# Wave 5 Go / No-Go Checklist

Use this checklist immediately before launch. If any item is no, stop and fix the setup before starting the sprint.

## Required

- [ ] The operator has read `docs_dev/wave5/WAVE5_EXECUTION_RUNBOOK.md`.
- [ ] The active scenario is `docs_dev/wave5/SCENARIO_DUBIZZLE_BUGFIX_SPRINT.md`.
- [ ] The reviewer preset is selected and understood.
- [ ] The current task pointer is loaded in `.orchestrator/tasks/current_task.json`.
- [ ] The task file contains the task ID expected for this sprint.
- [ ] `dispatch/gate-ralph/`, `dispatch/gate-architect/`, `dispatch/gate-critic/`, `dispatch/gate-monitor/`, and `dispatch/gate-playwright/` all exist.
- [ ] The watcher can write to `.orchestrator/logs/watcher.log`.
- [ ] `trace_hook()` can write to `.orchestrator/logs/decision_trace.log`.
- [ ] `audit_log()` can write to `.orchestrator/audit.log`.
- [ ] The monitor inbox path `dispatch/gate-monitor/inbox/` exists.
- [ ] `gate-monitor` is present in `cc_all`.
- [ ] `monitor_ingest.py` is enabled for the run.
- [ ] The commit gate input is expected to come from `.orchestrator/merged_verdicts/<task_id>.json`.
- [ ] The launcher dry-run, if used, matched the expected agent set.

## Operational Checks

- [ ] The reviewer preset matches the scenario, not a stale default.
- [ ] The operator knows which agent should receive the first review request.
- [ ] The operator knows where to look if a message does not arrive.
- [ ] The operator knows where to look if the monitor is silent.
- [ ] The operator knows what to do if the commit gate blocks.
- [ ] The operator has a results template ready to fill in during or after the run.

## No-Go Triggers

Do not launch if any of these are true:

- The task ID is missing or ambiguous.
- The watcher log is not writable.
- The decision trace path is not writable.
- The monitor inbox does not exist.
- The reviewer preset does not match the scenario.
- The operator cannot explain the recovery path for a missing review request.
- The operator cannot explain how to tell whether the commit gate should allow the next commit.

## Final Decision

- GO
- NO-GO

If the decision is NO-GO, record the reason here before leaving the sprint setup.
