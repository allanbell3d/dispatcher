#!/usr/bin/env python3
"""Contract checks for the canonical Dubizzle backlog file."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / ".orchestrator" / "tasks" / "tasks.json"


def test_tasks_have_required_fields_and_non_placeholder_acceptance():
    tasks = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    assert tasks
    for task in tasks:
        for field in ("task_id", "batch", "status", "title", "function", "details", "acceptance_criteria", "reference_paths"):
            assert field in task and task[field]
        assert isinstance(task["acceptance_criteria"], list) and task["acceptance_criteria"]
        assert isinstance(task["reference_paths"], list) and task["reference_paths"]
        for criterion in task["acceptance_criteria"]:
            assert "Same as" not in criterion


def test_tasks_have_no_mojibake_markers():
    text = TASKS_PATH.read_text(encoding="utf-8")
    assert "â" not in text
