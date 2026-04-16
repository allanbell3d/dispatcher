#!/usr/bin/env python3
"""Launcher actions should target the selected project root explicitly."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_passes_project_root_to_python_backed_actions():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert '& $PYTHON_EXE $orchCtl resume $ProjectRoot --agent $agentName --refan' in text
    assert '@("override", $ProjectRoot, "--task", $taskId, "--verdict", $verdict)' in text
    assert '& $PYTHON_EXE $orchCtl resume $ProjectRoot --agent $agentName' in text
    assert '& $PYTHON_EXE $validateScript $ProjectRoot' in text
