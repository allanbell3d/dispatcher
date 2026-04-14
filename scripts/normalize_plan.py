#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import re

from lib.common import atomic_write


FORBIDDEN = re.compile(r"\b(TODO|TBD|PLACEHOLDER|FIXME|XXX)\b")


def load_source(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"source file must contain JSON: {path}") from exc


def _validate_text(value, *, label: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if FORBIDDEN.search(value):
        raise ValueError(f"{label} contains forbidden placeholder")


def _validate_text_list(values, *, label: str) -> None:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label} must be a non-empty list")
    for value in values:
        _validate_text(value, label=label)


def normalize_plan(data, *, plan_id: str = "", title: str = "", description: str = "") -> dict:
    if isinstance(data, list):
        tasks = data
        resolved_plan_id = plan_id
        resolved_title = title or plan_id
        resolved_description = description
    elif isinstance(data, dict):
        tasks = data.get("tasks")
        resolved_plan_id = data.get("plan_id", plan_id)
        resolved_title = data.get("title", title or resolved_plan_id)
        resolved_description = data.get("description", description)
    else:
        raise ValueError("Plan source must be a JSON object or list")

    if not resolved_plan_id:
        raise ValueError("plan_id is required")
    _validate_text(resolved_plan_id, label="plan_id")
    _validate_text(resolved_title, label="title")
    if resolved_description:
        _validate_text(resolved_description, label="description")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty list")

    normalized_tasks = []
    seen_ids = set()
    for idx, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            raise ValueError(f"task #{idx} must be an object")
        task_id = str(task.get("task_id", "")).strip()
        title_value = str(task.get("title", "")).strip()
        acceptance = task.get("acceptance_criteria")
        refs = task.get("reference_paths")
        if not task_id:
            raise ValueError(f"task #{idx} missing task_id")
        if task_id in seen_ids:
            raise ValueError(f"duplicate task_id: {task_id}")
        seen_ids.add(task_id)
        if not title_value:
            raise ValueError(f"task {task_id} missing title")
        _validate_text(task_id, label=f"task #{idx} task_id")
        _validate_text(title_value, label=f"task {task_id} title")
        _validate_text_list(acceptance, label=f"task {task_id} acceptance_criteria")
        _validate_text_list(refs, label=f"task {task_id} reference_paths")
        normalized = {
            "task_id": task_id,
            "title": title_value,
            "acceptance_criteria": acceptance,
            "reference_paths": refs,
        }
        for optional in ("description", "deps", "owner", "notes"):
            if optional in task:
                value = task[optional]
                if isinstance(value, list):
                    _validate_text_list(value, label=f"task {task_id} {optional}")
                elif isinstance(value, str):
                    _validate_text(value, label=f"task {task_id} {optional}")
                normalized[optional] = value
        normalized_tasks.append(normalized)

    result = {
        "plan_id": resolved_plan_id,
        "title": resolved_title,
        "tasks": normalized_tasks,
    }
    if resolved_description:
        result["description"] = resolved_description
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a watcher-ingestible plan JSON file")
    parser.add_argument("source")
    parser.add_argument("--output", default="")
    parser.add_argument("--plan-id", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    source_path = Path(args.source)
    data = load_source(source_path)
    normalized = normalize_plan(
        data,
        plan_id=args.plan_id,
        title=args.title,
        description=args.description,
    )
    rendered = json.dumps(normalized, indent=2) + "\n"
    if args.output:
        atomic_write(Path(args.output), rendered)
        print(args.output)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
