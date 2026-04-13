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
    return json.loads(path.read_text(encoding="utf-8"))


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
        if not isinstance(acceptance, list) or not acceptance:
            raise ValueError(f"task {task_id} acceptance_criteria must be a non-empty list")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"task {task_id} reference_paths must be a non-empty list")
        for criterion in acceptance:
            if not isinstance(criterion, str):
                raise ValueError(f"task {task_id} acceptance criteria entries must be strings")
            if FORBIDDEN.search(criterion):
                raise ValueError(f"task {task_id} contains forbidden placeholder in acceptance_criteria")
        normalized = {
            "task_id": task_id,
            "title": title_value,
            "acceptance_criteria": acceptance,
            "reference_paths": refs,
        }
        for optional in ("description", "deps", "owner", "notes"):
            if optional in task:
                normalized[optional] = task[optional]
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
