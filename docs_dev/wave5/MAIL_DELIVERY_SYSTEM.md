# Mail Delivery System

This document explains how the Wave 5 dispatcher moves messages between agents.
It is operator-facing, not implementation-facing.

## Core Rule

Mail is file-based. A delivered message appears as a file in a recipient inbox under `dispatch/gate-*/inbox/`.

The watcher is the normal delivery path. Agents do not mail each other directly when the dispatcher is running normally.

## Message Types

- `review_request`
- `review_response`
- `direct_message`
- `activity`
- `merged`
- `fanin`
- `escalation`
- `pulse`
- `crash`

Not every run uses every type. The important part is that the operator knows which path should carry which kind of message.

## Expected Filenames

Delivered files are human-readable markdown files with a stamped name.

The general shape is:

- timestamp prefix
- sender or route prefix
- task hint
- random suffix
- `.md` extension

Example pattern:

- `20260414-153012-123456-from-gate-ralph-T42-4817.md`

Do not depend on the exact random suffix. Depend on the inbox path and the task ID.

## Watcher Delivery Rules

- `review_request` goes to the requested reviewer inboxes.
- `review_response` goes back to the originating executor or task owner.
- `cc_all` recipients get a copy when the route is configured for it.
- `gate-monitor` should receive live activity summaries through the watcher path.
- `fanin` produces the merged verdict path for the commit gate.
- `escalation` goes to the escalation target and any configured CC recipients.

## Safety Rules

- The sender outbox is not the same as the recipient inbox.
- Delivered mail may be archived after successful handoff.
- Undelivered mail should stay visible until it is actually delivered or manually resolved.
- Do not clear outboxes to hide a routing problem.

## What To Inspect When Nothing Arrives

1. Check the sender outbox.
2. Check `.orchestrator/logs/watcher.log`.
3. Check the recipient inbox path.
4. Check `cc_all` and the active route.
5. Check whether the target agent was online.
6. Check whether the message type matches the route you expected.

## What To Inspect When The Monitor Says It Saw Nothing

- `dispatch/gate-monitor/inbox/`
- `cc_all`
- `monitor_ingest.py`
- `.orchestrator/logs/watcher.log`

If the mail path is broken, fix the path. Do not simulate delivery by copying files into the inbox by hand.
