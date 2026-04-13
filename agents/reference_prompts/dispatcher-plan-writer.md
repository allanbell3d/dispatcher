# Dispatcher Plan Writer

Write watcher-ingestible plan JSON for `.orchestrator/plans/`.

## Output Rules

- Top-level keys:
  - `plan_id`
  - `title`
  - optional `description`
  - `tasks`
- Each task must contain:
  - `task_id`
  - `title`
  - `acceptance_criteria`
  - `reference_paths`
- `acceptance_criteria` must be a non-empty list of concrete testable statements
- `reference_paths` must be a non-empty list of repo-relative paths
- Do not use placeholder text such as `TODO`, `TBD`, `FIXME`, `XXX`, or `PLACEHOLDER`

## Good Example

```json
{
  "plan_id": "dispatcher-reviewer-rollout",
  "title": "Dispatcher Reviewer Rollout",
  "tasks": [
    {
      "task_id": "R1",
      "title": "Add reviewer presets",
      "acceptance_criteria": [
        "Config includes classic and codex reviewer presets",
        "Active reviewers can be switched without editing three separate arrays"
      ],
      "reference_paths": [
        ".orchestrator/config.json",
        "schemas/config_schema.json"
      ]
    }
  ]
}
```
