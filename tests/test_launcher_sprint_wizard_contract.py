#!/usr/bin/env python3
"""Launcher sprint wizard should validate, select a plan, and seed task dispatch."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_sprint_wizard_includes_plan_selection_and_validation():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'Sprint Wizard - Plan Selection' in text
    assert 'Save-SelectedPlanPath $selectedPlanPath' in text
    assert 'Invoke-OrchestratorCtl @("validate", $ProjectRoot)' in text
    assert 'SeedTasksFromPlan $selectedPlanPath' in text
    assert 'Dispatch-TaskById $firstTaskId $firstExecutor "launch_task"' in text


def test_launcher_waits_for_ready_files_with_feedback():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'function Wait-ForReadyFiles' in text
    assert 'Ready wait timed out' in text
    assert 'Ready files are advisory; continuing without' in text
