# Wave 5 Test Scenarios

## Happy Path

- coder receives task
- reviewers approve
- commit gate passes
- next task advances

## Rejection Path

- one reviewer rejects
- coder receives rework
- no commit allowed until fresh approval

## Timeout Path

- reviewer response missing
- watcher escalates
- monitor sees escalation

## Recovery Path

- operator uses resume / override as needed
