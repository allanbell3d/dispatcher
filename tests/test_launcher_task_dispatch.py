#!/usr/bin/env python3
"""Launcher should support task dispatch on launch and stuck-task re-dispatch."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_includes_task_dispatch_helpers():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'function Format-TaskDispatchBody' in text
    assert 'function Queue-TaskDispatch' in text
    assert 'TYPE: task' in text
    assert 'function Dispatch-TaskById' in text


def test_launcher_launch_and_resume_use_task_dispatch():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'resume_task' in text
    assert 'Dispatch-TaskById $taskId $agentName "resume_task"' in text
    assert 'Dispatch-TaskById $firstTaskId $firstExecutor "launch_task"' in text
