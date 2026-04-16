#!/usr/bin/env python3
"""Launcher should not retarget to a project root missing config.json."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_change_project_requires_config_json():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'No .orchestrator/config.json found at $target' in text
    assert 'Use this directory anyway?' not in text
