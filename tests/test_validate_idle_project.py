#!/usr/bin/env python3
"""Idle projects without task bootstrap should validate with warnings, not fail."""

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from tests.project_artifacts import build_project


ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate.py"


def _make_project() -> Path:
    base = ROOT / ".pytest_tmp_validate_idle"
    project = base / f"idle_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    build_project(project, project_name="idle-project-test")
    return project


def test_validate_accepts_idle_project_without_tasks_or_current_task():
    project = _make_project()
    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATE), str(project)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "RESULT: PASS" in output
        assert "no task" in output.lower()
    finally:
        shutil.rmtree(project, ignore_errors=True)
