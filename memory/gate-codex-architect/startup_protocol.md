# gate-codex-architect — Startup Protocol

## Phase 1: Identity

1. Read your notes: `D:/IA/dispatcher_repo/memory/gate-codex-architect/notes.md`
2. Report to Allan:
   ```text
   IDENTITY: gate-codex-architect
   ROLE: {your role from CLAUDE.md}
   MODEL: {your model}
   PERMISSIONS: {from CLAUDE.md}
   ```
3. STOP. Wait for Allan to confirm.

## Phase 2: Role Loading

4. Read your role instructions: `D:/IA/dispatcher_repo/agents/profiles/coordinated/gate-codex-architect/role_prompt.md`
5. Read any spec files listed in your role, if applicable.
6. Report to Allan:
   ```text
   ROLE LOADED: architect
   GATE DIR: D:/IA/dispatcher_repo/dispatch/gate-codex-architect
   MAILBOX: D:/IA/dispatcher_repo/dispatch/gate-codex-architect/inbox/
   STATUS: Ready for confirmation
   ```
7. STOP. Wait for Allan to confirm.

## Phase 3: Registration

8. Allan says "CONFIRMED" or "GO"
9. Create file: `D:/IA/dispatcher_repo/dispatch/gate-codex-architect/ready` with content `ready`
10. Report: `REGISTERED: architect - waiting for dispatch`
11. Enter idle state - wait for messages in your inbox

## IMPORTANT

- Do not read mailbox files until Phase 3 is complete
- Do not write outbox messages until dispatch begins
- Do not start any work until Allan explicitly starts the sprint
- If anything is wrong, stop and tell Allan
