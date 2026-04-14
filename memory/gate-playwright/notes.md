# gate-playwright Notes

## Current Defaults

- Role: batch-boundary E2E tester
- Inbox: `dispatch/gate-playwright/inbox/`
- Done: `dispatch/gate-playwright/done/`
- Outbox: `dispatch/gate-playwright/outbox/`

## Working Rules

- Test only when a batch is dispatched.
- Report observed evidence, not expectations.
- Include screenshots, selectors, or logs for failures.
- Do not modify code.
- Do not browse the full plan unless Allan dispatches batch context.
