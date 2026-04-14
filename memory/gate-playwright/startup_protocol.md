# gate-playwright Startup Protocol

1. Read `memory/gate-playwright/notes.md`.
2. Read `agents/profiles/coordinated/gate-playwright/role_prompt.md`.
3. Confirm you are `gate-playwright`.
4. Wait for a batch-boundary message in `dispatch/gate-playwright/inbox/`.
5. After pickup, move the message to `dispatch/gate-playwright/done/`.
6. Run only the tests that match the dispatched batch context.
