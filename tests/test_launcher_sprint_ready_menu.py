#!/usr/bin/env python3
"""Launcher should surface sprint preflight separately from config validation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_exposes_sprint_ready_action_and_handler():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "Sprint Ready Check" in text
    assert "Invoke-SprintReady" in text
    assert 'type="sprint_ready"' in text or "type='sprint_ready'" in text
