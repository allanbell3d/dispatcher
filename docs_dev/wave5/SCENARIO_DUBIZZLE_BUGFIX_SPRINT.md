# Scenario: Dubizzle Bugfix Sprint

This is the canonical Wave 5 practice scenario. It uses a real bugfix-style backlog shape without requiring a broad platform change.

## Scenario Summary

- Sprint type: bugfix
- Backlog source: Dubizzle issues or the current Dubizzle-flavored task batch
- Primary executor: `gate-ralph`
- Reviewers: `gate-architect` and `gate-critic`
- Monitor: `gate-monitor`
- Batch tester: `gate-playwright`
- Commit gate: unanimous approval from the active reviewer preset

## Why This Scenario

This scenario is useful because it exercises the full dispatcher loop without turning into a giant rewrite:

- one executor
- two reviewers
- one monitor
- one batch tester
- a real commit gate

That is enough to prove the live orchestration path.

## Sprint Shape

1. Load one task batch into `.orchestrator/tasks/current_task.json`.
2. Let `gate-ralph` start the first fix.
3. Route the review request to both reviewers.
4. Route a copy to `gate-monitor`.
5. Wait for reviewer consensus in `.orchestrator/merged_verdicts/`.
6. Allow the commit gate to decide from the merged verdict.
7. Advance only when the current task is complete and the batch boundary rules say to continue.

## Reviewer Preset

Use the live unanimous reviewer pair for this scenario:

- `gate-architect`
- `gate-critic`

The operator should not improvise a third reviewer or a different approval model during the run.

## Expected Operator Behavior

- Keep the task batch fixed for the duration of the run.
- Do not swap scenarios halfway through.
- Do not manually edit merged verdict files to force progress.
- Record every rework cycle in the results template.

## Success Criteria

- The first task loads cleanly.
- The review request reaches both reviewers.
- The monitor sees live activity.
- The merged verdict file appears for the task.
- The commit gate behaves consistently with that verdict.
- The next task only starts when the sprint rules allow it.

## Exit Condition

The scenario is complete when the final task in the chosen batch is done and the operator has a clean result record with no missing evidence.
