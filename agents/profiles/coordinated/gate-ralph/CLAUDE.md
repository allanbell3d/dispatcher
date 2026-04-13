# gate-ralph

**Mode:** coordinated  
**Role:** Persistent executor.

Load this profile only for coordinated orchestration work.

Read your shared role prompt:
- `{shared_agents_root}/profiles/coordinated/gate-ralph/role_prompt.md`

Then read your project overlay:
- `memories/gate-ralph/notes.md`
- `memories/gate-ralph/startup_protocol.md`

Live communication:
- inbound: `dispatch/ralph/active/`
- outbound: `dispatch/ralph/outbox/`
- structured replies: `dispatch/ralph/reports/`

Private project control plane:
- `.orchestrator/`

Do not self-discover work from `.orchestrator/tasks/` unless Allan explicitly tells you to inspect it.

Work only the dispatched task, stop at the review gate, and do not self-serve the backlog.
