# Agents

## Team Composition

Defined in `.orchestrator/config.json`. The engine doesn't care who's on the team — it reads the config and routes accordingly. Use `bin/orch_launcher.ps1` as the primary operator UI; `bin/launch.ps1` and `bin/launch.sh` are legacy fossils.

Current default team:

| Agent | Profile | Executor | Roles | Description |
|-------|---------|----------|-------|-------------|
| gate-ralph | gate-ralph | Yes | coder | Writes code. Gets one task at a time. Cannot see the plan, other agents' reports, or reviewer verdicts. |
| gate-architect | gate-architect | No | reviewer | Reviews diffs for spec compliance, architecture decisions, contract alignment. Must approve before merge. |
| gate-critic | gate-critic | No | reviewer | Reviews diffs for correctness, edge cases, KISS violations, over-engineering. Must approve before merge. |
| gate-monitor | gate-monitor | No | monitor, playwright | Watches coder activity live via PostToolUse hooks. Halts on drift. CC'd on all routing. |
| gate-playwright | gate-playwright | No | tester | Runs E2E tests after batch completion. Results route to gate-ralph for fixes. |

## Identity Model

- Names are **gate-prefixed everywhere**: config, env var, dispatch folders, halt flags (`.flag`), routing
- `GATE_AGENT_NAME` env var is set per psmux session by the launcher
- No name stripping, no name building, no transformation at any layer
- `gate-ralph` in config = `gate-ralph` in env = `dispatch/gate-ralph/inbox/`

## Profiles

### Coordinated (gated sprints)
Located at `agents/profiles/coordinated/gate-*/`:
- `CLAUDE.md` — agent-specific Claude Code instructions
- `role_prompt.md` — role definition, constraints, communication protocol

These profiles are loaded when agents run inside a gated sprint session.

### Standalone (direct work)
Located at `agents/profiles/standalone/*/`:
- `CLAUDE.md` — agent instructions for working outside sprint context

Used when Allan wants an agent to do focused work without the gate machinery.

## Routing

Defined in `config.routing`:

```
review_requests_to  → [gate-architect, gate-critic]    Fan-out: coder delivers → both reviewers
cc_all              → [gate-monitor]                    Monitor sees everything
on_batch_complete   → [gate-playwright]                 Tests run after batch
on_test_failure     → [gate-ralph]                      Failed tests go back to coder
on_test_passed      → [gate-ralph]                      Passed tests advance the sprint
on_stop             → [gate-architect, gate-critic, gate-monitor]   Stop notification
escalation_target   → allan                             Timeout/conflict escalation
```

## Consensus

```json
{
  "require_approvals_from": ["gate-architect", "gate-critic"],
  "consensus_rule": "unanimous",
  "max_rework_rounds": 3
}
```

Both reviewers must approve. If either rejects, rework goes back to gate-ralph. After 3 failed rounds, escalate to Allan.

To change: edit `config.gate`. Want majority? Change `consensus_rule`. Want 3 reviewers? Add to both `agents[]` and `require_approvals_from`. Zero code changes.

## Communication

Agents communicate through `dispatch/<agent>/` folders:

| Folder | Purpose | Written by |
|--------|---------|-----------|
| `inbox/` | Incoming messages (tasks, review requests, test results) | Watcher only |
| `outbox/` | Outgoing messages (deliveries, verdicts, requests) | Owning agent only |
| `reports/` | Structured reports (review reports, test results) | Owning agent only |
| `done/` | Processed inbox items (moved after consumption) | Hook (on_file_message) |
| `archive/` | Long-term storage of processed outbox items | Watcher only |

Single-writer per file. No locks, no merge logic.
