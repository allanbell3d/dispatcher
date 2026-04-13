# Wave 5 Agent Initialization Sequence

This is the order to bring the mixed-agent sprint online. Keep the sequence simple and do not jump ahead.

## 1. Operator And Launcher

- Read the scenario and go/no-go docs.
- Confirm `.orchestrator/tasks/current_task.json` is loaded.
- Confirm the dispatcher launcher is pointed at the live repo root.
- Create or confirm the runtime dispatch folders under `dispatch/gate-*/`.

Do not start any agent sessions before this step is complete.

## 2. Watcher

- Start the watcher after the runtime folders exist.
- Confirm it can write to `.orchestrator/logs/watcher.log`.
- Confirm it can write merged verdicts to `.orchestrator/merged_verdicts/`.

The watcher is the delivery spine for the sprint. If it is unhealthy, the rest of the run is noisy or stalled.

## 3. Executor: gate-ralph

- Read `memory/gate-ralph/startup_protocol.md` before work begins.
- Read the current task pointer and the scenario summary.
- Watch `dispatch/gate-ralph/inbox/`.
- Write work progress to `dispatch/gate-ralph/outbox/` and `dispatch/gate-ralph/reports/` only.

Do not write into reviewer or monitor inboxes directly.

## 4. Reviewers: gate-architect And gate-critic

- Read their startup protocols and the scenario.
- Watch `dispatch/gate-architect/inbox/` and `dispatch/gate-critic/inbox/`.
- Return approvals or rejections through their outboxes and reports.
- Keep reviewer feedback tied to the current task ID.

These agents are the commit gate. If they are not loaded, the sprint is not live yet.

## 5. Monitor: gate-monitor

- Read `memory/gate-monitor/startup_protocol.md`.
- Watch `dispatch/gate-monitor/inbox/`.
- Confirm that live activity is arriving through the watcher and hook streams.
- Report drift or blind spots promptly.

The monitor should see the sprint, not just hear about it later.

## 6. Playwright: gate-playwright

- Read the startup protocol before the first test cycle.
- Watch `dispatch/gate-playwright/inbox/`.
- Run the batch-end checks only when the scenario says the batch is ready.

## 7. Operator Close Check

Before declaring the sprint live, confirm:

- the executor is online
- both reviewers are online
- the monitor is online
- the watcher is online
- the current task is loaded
- the launch sequence did not skip a step

If any step was skipped, restart the initialization sequence instead of improvising.
