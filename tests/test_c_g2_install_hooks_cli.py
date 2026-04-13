#!/usr/bin/env python3
"""Installer CLI test via scripts/orchestratorctl.py."""

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTL = ROOT / "scripts" / "orchestratorctl.py"

_CONFIG = {
    "project": "g2-test",
    "shared_roots": {
        "orchestrator_primary": str(ROOT),
        "orchestrator_fallback": str(ROOT),
        "agents_primary": str(ROOT),
        "agents_fallback": str(ROOT),
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "plans": ".orchestrator/plans",
        "tasks": ".orchestrator/tasks",
        "diffs": ".orchestrator/diffs",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True},
        {"name": "gate-architect", "executor": False},
    ],
    "gate": {},
    "routing": {},
    "fan_in": {},
    "wake": {},
    "session": {},
}


def write_config(project: Path) -> None:
    (project / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (project / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")


def make_project_dir() -> Path:
    base = ROOT / ".tmp_install_hooks_tests"
    project = base / f"g2_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    project.mkdir(parents=True, exist_ok=True)
    return project


def test_orchestratorctl_install_hooks_writes_shared_settings_file():
    project = make_project_dir()
    try:
        write_config(project)

        result = subprocess.run(
            [sys.executable, str(CTL), "install-hooks", str(project)],
            capture_output=True,
            text=True,
            cwd=str(project),
        )

        assert result.returncode == 0, result.stderr
        settings_path = project / ".claude" / "settings.local.json"
        assert settings_path.exists()

        data = json.loads(settings_path.read_text(encoding="utf-8"))
        file_changed = data["hooks"]["FileChanged"]
        assert any(entry["matcher"] == "dispatch/gate-ralph/inbox/*.md" for entry in file_changed)
        assert any(entry["matcher"] == "dispatch/gate-ralph/inbox/*.json" for entry in file_changed)
        assert any(entry["matcher"] == "dispatch/gate-architect/inbox/*.md" for entry in file_changed)
        assert any(entry["matcher"] == "dispatch/gate-architect/inbox/*.json" for entry in file_changed)
        assert "written to" in result.stdout
        assert "merged hooks for 2 agents" in result.stdout
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_orchestratorctl_render_hooks_keeps_single_agent_json_mode():
    project = make_project_dir()
    try:
        write_config(project)

        result = subprocess.run(
            [sys.executable, str(CTL), "render-hooks", str(project), "--agent", "gate-ralph"],
            capture_output=True,
            text=True,
            cwd=str(project),
        )

        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert "hooks" in data
        assert not (project / ".claude" / "settings.local.json").exists()
    finally:
        shutil.rmtree(project, ignore_errors=True)
