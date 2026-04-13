# Mail Delivery System

## Primary Paths

- outbound: `dispatch/<agent>/outbox/`
- inbound: `dispatch/<agent>/inbox/`
- structured reports: `dispatch/<agent>/reports/`
- processed mail: `dispatch/<agent>/done/`
- archived outbound: `dispatch/<agent>/archive/`

## Message Types

- `review_request`
- `review_response`
- `fan_in_complete`
- `escalation`
- `pulse`
- `activity`

## Rules

- watcher fans review requests to the active reviewer set
- CC traffic goes to `routing.cc_all`
- outbox items archive only after real delivery
