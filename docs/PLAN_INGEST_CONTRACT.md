# Dispatcher Plan Ingest Contract

This document is the approved contract for watcher-ingestible plans in `.orchestrator/plans/*.json`.

## Canonical Shape

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
      "reference_paths": ["service/dubizzle.py"],
      "deps": ["B0"],
      "description": "Optional task notes",
      "owner": "gate-ralph",
      "notes": "Optional implementation notes"
    }
  ]
}
```

## Required Fields

- `plan_id` is required at the top level
- `title` is required at the top level
- `tasks` is required and must be a non-empty list
- every task must include `task_id`, `title`, `acceptance_criteria`, and `reference_paths`
- `acceptance_criteria` must be a non-empty list of strings
- `reference_paths` must be a non-empty list of repo-relative strings

## Supported Optional Fields

- top-level `description`
- task-level `description`
- task-level `deps`
- task-level `owner`
- task-level `notes`

`deps` is supported as structured dependency metadata and should be used instead of hiding relationships only in prose when a task depends on another task.

## Placeholder Rule

Placeholder text is not allowed in plan content.

Rejected tokens include:

- `TODO`
- `TBD`
- `FIXME`
- `XXX`
- `PLACEHOLDER`

This applies to `title`, `description`, `acceptance_criteria`, `reference_paths`, and other text fields that reach the watcher.

## Normalization Behavior

`scripts/normalize_plan.py` accepts either:

- a full plan object with `plan_id`, `title`, and `tasks`
- a bare task list when `--plan-id` is supplied

The normalizer:

- preserves task order
- preserves supported optional task fields
- rejects duplicate `task_id` values
- fails clearly when the source is not JSON

## Example Usage

```powershell
python scripts/normalize_plan.py input.json --plan-id my-plan --title "My Plan"
```

Use this helper to turn draft plan JSON into watcher-safe output before placing it under `.orchestrator/plans/`.
