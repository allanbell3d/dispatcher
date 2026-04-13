# Watcher Liveness Ticker — Spec

**Component:** #18 (Watcher liveness / idle-wake)
**Owner:** Allan
**Location:** Separate thread in `dispatcher/orchestrator/scripts/watcher.py`

---

## Purpose

Re-wake agents that have fallen asleep (compaction, context shift, model stall, user inactivity). But ONLY if they have work to do. Blind waking is noise.

---

## Core rule

**Only wake an agent that has unread items in their inbox.** An idle agent with an empty inbox is correctly idle — leave it alone.

---

## Wake decision matrix

| Agent role | Inbox has items | Idle beyond threshold | Action |
|---|---|---|---|
| Coder | Yes (task file) | Yes | WAKE — has work to do |
| Coder | No | Yes | SKIP — no task dispatched, WAITING is correct |
| Reviewer | Yes (review request) | Yes | WAKE — review pending |
| Reviewer | No | Yes | SKIP — nothing to review |
| Monitor | Yes (cc/ingest) | Yes | WAKE — has observations to process |
| Monitor | No | Yes | SKIP — no new data |
| Any | Any | No | SKIP — not idle yet |

**Simple implementation:** for each agent, check `dispatch/<agent>/inbox/` file count > 0 AND idle time > threshold. Both conditions must be true to wake.

---

## Mechanism

- Separate thread in watcher (never blocks COPY/MERGE/DISTRIBUTE main loop)
- Runs every `config.wake.liveness_check_interval_seconds` (default 30s)
- For each agent in `config.agents[]`:
  1. Check `state_root/last_tool_use/<agent>.ts` — if missing, agent never registered (skip)
  2. If age < `config.wake.idle_threshold_seconds` (default 120s) → skip (not idle)
  3. Check `dispatch/<agent>/inbox/` — if empty → skip (no work)
  4. Both conditions met → call `wake_agent(name, config.wake.mechanism)` + log

---

## Logging

Every liveness tick logs to decision trace (Component 22):

```json
{"ts": "...", "hook": "liveness", "agent": "architect", "decision": "skip", "reason": "inbox empty", "inbox_count": 0, "idle_seconds": 180}
{"ts": "...", "hook": "liveness", "agent": "ralph", "decision": "wake", "reason": "inbox has 1 item, idle 150s", "inbox_count": 1, "idle_seconds": 150}
```

Dual-write: NAS archive + project-local.

---

## Edge cases

- **Agent never created `last_tool_use` file:** Skip — agent hasn't started yet or isn't instrumented. Don't spam wake a session that never initialized.
- **Inbox has only `.tmp` files:** Don't count `.tmp` as work items. Use same filter as dispatch_gate: `p.is_file() and p.suffix != ".tmp"`.
- **Watcher itself is the only writer to `last_tool_use/`:** The PostToolUse hook on each agent writes the timestamp. If the hook isn't installed, the file won't exist → agent is skipped. This is correct — an agent without hooks isn't gated and doesn't need liveness wake.
- **Multiple wake retries:** Don't re-wake an agent that was already woken within `config.wake.retry_interval_seconds`. Track last-wake-time per agent in memory (not persisted — resets on watcher restart, which is fine).

---

## What this does NOT do

- **Health check:** doesn't verify agent is responsive. A woken agent that ignores the wake is a problem for `orch status` / Allan, not for the ticker.
- **Restart stuck agents:** beyond scope. Ticker only sends wake signals.
- **Complex stall detection:** POC scope is inbox + idle time only. Pattern analysis (e.g., "agent has been on same task for 30 min") is post-POC.

---

## Acceptance

- Agent with inbox items + idle 150s (threshold 120s) → wake fires within 30s
- Agent with empty inbox + idle 150s → NO wake
- Agent with inbox items + idle 60s (threshold 120s) → NO wake (not idle enough)
- Main watcher loop processes messages during the liveness check without delay
- Decision trace log records every wake/skip with reason and inbox count
- No hardcoded agent names — reads from config.agents[]
