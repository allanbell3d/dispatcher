# Dispatcher — Agent Roster

Agents are declared in `.orchestrator/config.json` under `agents[]`. The engine is agnostic — names, roles, and count are config-driven.

## Default team (from spec)

| Agent | Role | Model | Profile |
|---|---|---|---|
| gate-ralph | coder (executor) | Sonnet | `agents/profiles/coordinated/gate-ralph/role_prompt.md` |
| gate-architect | reviewer | Opus | `agents/profiles/coordinated/gate-architect/role_prompt.md` |
| gate-critic | reviewer | Opus | `agents/profiles/coordinated/gate-critic/role_prompt.md` |
| gate-monitor | observer + playwright | Opus | `agents/profiles/coordinated/gate-monitor/role_prompt.md` |

## Identity

Each agent's identity is set by the launcher via `$env:GATE_AGENT_NAME` before Claude starts. All hooks read this env var. No file-read detection.

## Dispatch folders

Each agent gets: `dispatch/<name>/inbox/`, `outbox/`, `reports/`, `done/`, `archive/`

## Adding/removing agents

Edit `config.agents[]`, `routing`, `gate.require_approvals_from`, `fan_in.review.required`. Run `orch install-hooks --all`. Zero engine code changes.
