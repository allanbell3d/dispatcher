# Monitor Agent Setup

`gate-monitor` is the live observer for Wave 5. Its job is to notice what is happening, not to become the bottleneck.

## What The Monitor Receives

The monitor should receive two kinds of input:

- direct watcher-delivered messages in `dispatch/gate-monitor/inbox/`
- hook-generated activity summaries when `monitor_ingest.py` is enabled

The live feed is the inbox. Everything else is supporting evidence.

## What The Monitor Watches

- `dispatch/gate-monitor/inbox/`
- `dispatch/gate-monitor/reports/`
- `.orchestrator/logs/watcher.log`
- `.orchestrator/logs/decision_trace.log`
- `.orchestrator/audit.log`

The monitor should use these paths to answer three questions:

1. Did the right message arrive?
2. Did it arrive on time?
3. Did the system behave the way the scenario said it should?

## Setup Steps

1. Confirm `gate-monitor` exists in the active dispatcher config.
2. Confirm `gate-monitor` is included in `cc_all`.
3. Confirm `dispatch/gate-monitor/inbox/` exists.
4. Confirm `monitor_ingest.py` is enabled for the run.
5. Confirm the watcher is running.
6. Confirm messages are appearing in the inbox.

## Expected Message Shape

Monitor inbox files should be short, readable, and tied to a specific tool call or delivery event.

Typical contents should include:

- sender
- task ID
- tool name or delivery type
- timestamp
- concise summary of the action

## Failure Symptoms

Treat these as real failures, not just cosmetic noise:

- `dispatch/gate-monitor/inbox/` stays empty while other agents are active
- the watcher log shows delivery attempts but no files appear
- the monitor only sees old messages
- the monitor receives summaries but they are missing task IDs
- `gate-monitor` is not in `cc_all`
- `monitor_ingest.py` was disabled for the run

## Operator Response

If the monitor is silent:

1. Check the watcher log.
2. Check `cc_all`.
3. Check whether `monitor_ingest.py` is enabled.
4. Check whether the monitor inbox path exists.
5. Check whether the current task is actually generating activity.

Do not fix monitor silence by hand-writing fake inbox messages. Repair the delivery path instead.
