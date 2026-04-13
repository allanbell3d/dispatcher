#!/usr/bin/env python3
"""Launcher deploy-to-project must guard against self-copying config.json."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_deploy_to_project_has_self_copy_guard_for_config_json():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "already current project, skipped copy" in text
