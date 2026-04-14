#!/usr/bin/env python3
"""Strict sprint preflight checks for active sprint execution."""

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from tests.project_artifacts import build_project, write_artifact_json


ROOT = Path(__file__).resolve().parents[1]
SPRINT_READY = ROOT / "scripts" / "sprint_ready.py"
CTL = ROOT / "scripts" / "orchestratorctl.py"


def _make_project() -> Path:
    base = ROOT / ".pytest_tmp_sprint_ready"
    project = base / f"sprint_ready_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    build_project(project, project_name="sprint-ready-test")
    return project


def _run(script: Path, project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), str(project)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


def _write_task(project: Path, task_id: str = "TASK-001") -> None:
    write_artifact_json(
        project,
        f".orchestrator/tasks/{task_id}.json",
        "fixtures/tasks/prepared_task.json",
        overrides={"task_id": task_id},
    )


def _write_current_task(project: Path, task_id: str = "TASK-001") -> None:
    write_artifact_json(
        project,
        ".orchestrator/tasks/current_task.json",
        "fixtures/tasks/current_task.ready.json",
        overrides={"task_id": task_id},
    )


def test_sprint_ready_fails_for_idle_project_without_tasks():
    project = _make_project()
    try:
        result = _run(SPRINT_READY, project)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "idle" in output.lower() or "no task" in output.lower()
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_sprint_ready_fails_when_tasks_exist_but_no_current_task_selected():
    project = _make_project()
    try:
        _write_task(project)
        result = _run(SPRINT_READY, project)
        output = result.stdout + result.stderr
        assert result.returncode != 0, output
        assert "current task" in output.lower()
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_sprint_ready_passes_when_current_task_references_existing_task():
    project = _make_project()
    try:
        _write_task(project)
        _write_current_task(project)
        result = _run(SPRINT_READY, project)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "ready" in output.lower()
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_orchestratorctl_sprint_ready_command_delegates_to_preflight():
    project = _make_project()
    try:
        _write_task(project)
        _write_current_task(project)
        result = subprocess.run(
            [sys.executable, str(CTL), "sprint-ready", str(project)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "ready" in output.lower()
    finally:
        shutil.rmtree(project, ignore_errors=True)
