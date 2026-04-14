#!/usr/bin/env python3
"""Tests for scripts/normalize_plan.py."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_plan.py"


def _temp_path(name: str) -> Path:
    base = ROOT / ".pytest_tmp_plan_normalization"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{name}.json"


def test_normalize_plan_preserves_optional_fields_and_is_deterministic():
    data = {
        "plan_id": "demo-plan",
        "title": "Demo Plan",
        "description": "Demo description",
        "tasks": [
            {
                "task_id": "P1",
                "title": "First task",
                "description": "Task notes",
                "deps": ["P0"],
                "owner": "gate-ralph",
                "notes": "Keep it simple",
                "acceptance_criteria": ["Does the thing"],
                "reference_paths": ["service/foo.py"],
            }
        ],
    }

    from scripts.normalize_plan import normalize_plan

    first = normalize_plan(data)
    second = normalize_plan(data)

    assert first == second
    assert first == {
        "plan_id": "demo-plan",
        "title": "Demo Plan",
        "tasks": [
            {
                "task_id": "P1",
                "title": "First task",
                "acceptance_criteria": ["Does the thing"],
                "reference_paths": ["service/foo.py"],
                "description": "Task notes",
                "deps": ["P0"],
                "owner": "gate-ralph",
                "notes": "Keep it simple",
            }
        ],
        "description": "Demo description",
    }


def test_normalize_plan_rejects_placeholder_in_plan_header():
    from scripts.normalize_plan import normalize_plan

    with pytest.raises(ValueError, match="title contains forbidden placeholder"):
        normalize_plan(
            {
                "plan_id": "demo-plan",
                "title": "TODO plan",
                "tasks": [
                    {
                        "task_id": "P1",
                        "title": "First task",
                        "acceptance_criteria": ["Does the thing"],
                        "reference_paths": ["service/foo.py"],
                    }
                ],
            }
        )


def test_normalize_plan_rejects_placeholders_outside_acceptance_criteria():
    source = _temp_path("placeholder_source")
    source.write_text(
        json.dumps(
            [
                {
                    "task_id": "P2",
                    "title": "TODO task",
                    "acceptance_criteria": ["Does the thing"],
                    "reference_paths": ["service/TBD.py"],
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), "--plan-id", "bad-plan"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode != 0
        assert "forbidden placeholder" in (result.stderr + result.stdout)
    finally:
        source.unlink(missing_ok=True)


def test_normalize_plan_fails_clearly_on_non_json_input():
    source = _temp_path("markdown_source")
    source.write_text("# Draft plan\n\n- task one\n", encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), "--plan-id", "markdown-plan"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode != 0
        assert "JSON" in (result.stderr + result.stdout)
    finally:
        source.unlink(missing_ok=True)


@pytest.mark.parametrize(
    "bad_task, expected",
    [
        ({"title": "Missing id", "acceptance_criteria": ["ok"], "reference_paths": ["a.py"]}, "missing task_id"),
        ({"task_id": "P3", "acceptance_criteria": ["ok"], "reference_paths": ["a.py"]}, "missing title"),
        ({"task_id": "P4", "title": "Bad", "reference_paths": ["a.py"]}, "acceptance_criteria"),
        ({"task_id": "P5", "title": "Bad", "acceptance_criteria": ["ok"]}, "reference_paths"),
        (
            {
                "task_id": "P6",
                "title": "Bad",
                "acceptance_criteria": ["ok"],
                "reference_paths": ["TODO.md"],
            },
            "forbidden placeholder",
        ),
    ],
)
def test_normalize_plan_rejects_invalid_tasks(bad_task, expected):
    from scripts.normalize_plan import normalize_plan

    with pytest.raises(ValueError, match=expected):
        normalize_plan({"plan_id": "plan", "title": "Plan", "tasks": [bad_task]})
