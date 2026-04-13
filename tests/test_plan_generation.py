#!/usr/bin/env python3
"""Tests for scripts/normalize_plan.py."""

import json
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_plan.py"


def _temp_path(name: str) -> Path:
    base = ROOT / ".pytest_tmp_plan_generation"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{name}_{uuid.uuid4().hex}.json"


def test_normalize_plan_from_task_list():
    source = _temp_path("source")
    try:
        source.write_text(json.dumps([
            {
                "task_id": "P1",
                "title": "Task one",
                "acceptance_criteria": ["Does the thing"],
                "reference_paths": ["service/foo.py"],
            }
        ], indent=2), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), "--plan-id", "plan-one", "--title", "Plan One"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["plan_id"] == "plan-one"
        assert data["title"] == "Plan One"
        assert data["tasks"][0]["task_id"] == "P1"
    finally:
        source.unlink(missing_ok=True)


def test_normalize_plan_rejects_placeholders():
    source = _temp_path("bad")
    try:
        source.write_text(json.dumps([
            {
                "task_id": "P2",
                "title": "Task two",
                "acceptance_criteria": ["TODO later"],
                "reference_paths": ["service/bar.py"],
            }
        ], indent=2), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), "--plan-id", "bad-plan"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode != 0
        assert "forbidden placeholder" in result.stderr or "forbidden placeholder" in result.stdout
    finally:
        source.unlink(missing_ok=True)
