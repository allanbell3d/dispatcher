#!/usr/bin/env python3
"""Launcher deploy-engine should use immutable engine source semantics."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_deploy_engine_uses_engine_root_and_includes_agents():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert '$engineSource = $EngineRoot' in text
    assert '"agents\\profiles"' in text
    assert '"agents\\protocols"' in text
    assert '"sprint_profiles"' not in text.split('function Invoke-DeployEngine {', 1)[1].split('function Invoke-DeployAgents {', 1)[0]
