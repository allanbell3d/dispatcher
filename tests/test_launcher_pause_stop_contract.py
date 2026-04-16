#!/usr/bin/env python3
"""Launcher pause/stop surfaces should expose operator-facing sprint state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_dashboard_marks_paused_when_executor_halts_exist():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert '$sprintLabel = "PAUSED"' in text
    assert 'Join-Path $HaltsDir "$($agent[\'name\']).flag"' in text


def test_launcher_stop_summary_includes_counts_and_total_time():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'Tasks completed:' in text
    assert 'Tasks remaining:' in text
    assert 'Total time:' in text
