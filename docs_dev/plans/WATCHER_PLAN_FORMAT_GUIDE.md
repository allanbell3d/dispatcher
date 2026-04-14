# Watcher Plan Format Guide

## Canonical Shape

Watcher-ingestible plans live under `.orchestrator/plans/*.json` and use this top-level shape:

```json
{
  "plan_id": "dubizzle-bugfix-full",
  "title": "Dubizzle Bugfix Sprint",
  "description": "Optional summary",
  "tasks": [
    {
      "task_id": "B1",
      "title": "Fresh form fills nothing",
      "acceptance_criteria": [
        "After category selection, bot waits for the first form field to render"
      ],
      "reference_paths": ["service/dubizzle.py"]
    }
  ]
}
```

## Rules

- `plan_id` is required
- every task needs `task_id`, `title`, `acceptance_criteria`, and `reference_paths`
- `acceptance_criteria` must be a non-empty list of strings
- `reference_paths` must be a non-empty list
- placeholder text like `TODO`, `TBD`, `FIXME`, `XXX`, `PLACEHOLDER` is rejected

## Rejected Example

```json
{
  "plan_id": "bad-plan",
  "tasks": [
    {
      "task_id": "P1",
      "title": "Something",
      "acceptance_criteria": ["TODO later"],
      "reference_paths": ["service/foo.py"]
    }
  ]
}
```

## Helper

Use:

```powershell
python scripts/normalize_plan.py input.json --plan-id my-plan
```

to normalize a loose task list into the canonical watcher plan shape.
