#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse

from lib.common import (
    agent_names,
    current_task_id,
    load_project_config,
    read_json,
    resolve_path,
    resolve_project_root,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strict preflight for starting a gated sprint on a prepared project"
    )
    parser.add_argument("project", nargs="?", default=None)
    args = parser.parse_args()

    project_root = resolve_project_root(args.project)
    config = load_project_config(project_root)

    errors: list[str] = []

    for key in ["dispatch_root", "state_root", "tasks", "plans"]:
        path = resolve_path(key, project_root, config)
        if not path.exists():
            errors.append(f"missing required path ({key}): {path}")

    dispatch_root = resolve_path("dispatch_root", project_root, config)
    for agent in agent_names(config):
        for sub in ["inbox", "outbox", "reports", "done", "archive"]:
            path = dispatch_root / agent / sub
            if not path.exists():
                errors.append(f"dispatch folder missing: dispatch/{agent}/{sub}")

    tasks_dir = resolve_path("tasks", project_root, config)
    current_task_path = resolve_path("current_task", project_root, config)

    task_files = sorted(tasks_dir.glob("*.json")) if tasks_dir.is_dir() else []
    tasks = []
    for task_file in task_files:
        if task_file.name == current_task_path.name:
            continue
        data = read_json(task_file, None)
        if isinstance(data, list):
            tasks.extend(data)
        elif isinstance(data, dict):
            tasks.append(data)

    if not tasks:
        errors.append("no task files present in .orchestrator/tasks — project is idle, not sprint-ready")
    else:
        task_ids = set()
        for index, task in enumerate(tasks, 1):
            task_id = current_task_id(task)
            if not task_id:
                errors.append(f"task #{index} missing task_id")
            if not str(task.get('title') or '').strip():
                errors.append(f"task #{index} missing title")
            acceptance = task.get("acceptance_criteria")
            if not isinstance(acceptance, list) or not acceptance:
                errors.append(f"task #{index} acceptance_criteria must be a non-empty list")
            references = task.get("reference_paths")
            if not isinstance(references, list):
                errors.append(f"task #{index} reference_paths must be a list")
            if task_id:
                if task_id in task_ids:
                    errors.append(f"duplicate task id: {task_id}")
                task_ids.add(task_id)

        current = read_json(current_task_path, {})
        active_task_id = current_task_id(current)
        if not active_task_id:
            errors.append("no active current task selected (current_task.json missing, empty, or invalid)")
        elif active_task_id not in task_ids:
            errors.append(f"current task {active_task_id} not present in tasks")

    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        print("RESULT: FAIL")
        return 1

    print(f"RESULT: PASS — sprint-ready {project_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
