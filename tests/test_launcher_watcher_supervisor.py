#!/usr/bin/env python3
"""Launcher watcher supervisor should start watcher with explicit project root context."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_watcher_supervisor_passes_project_root():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert '$escapedProjectRoot' in text
    assert "Start-Process `$python -ArgumentList @(`$watcherScript, `$projectRoot) -WorkingDirectory `$projectRoot" in text
