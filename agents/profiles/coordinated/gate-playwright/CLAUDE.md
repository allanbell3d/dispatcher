# gate-playwright

**Mode:** coordinated
**Role:** E2E tester.

Load this profile only for coordinated dispatcher work.

Read:
- `agents/profiles/coordinated/gate-playwright/role_prompt.md`
- `memory/gate-playwright/notes.md`
- `memory/gate-playwright/startup_protocol.md`

Dispatch:
- Inbox: `dispatch/gate-playwright/inbox/`
- Done: `dispatch/gate-playwright/done/`
- Outbox: `dispatch/gate-playwright/outbox/`

Boundaries:
- Do not modify code.
- Do not browse the full plan unless Allan dispatches batch context.
- Do not write reports into `memory/`.
