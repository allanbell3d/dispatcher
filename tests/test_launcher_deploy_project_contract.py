#!/usr/bin/env python3
"""Launcher deploy-to-project should stay non-destructive and seed config from artifacts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_deploy_to_project_uses_seed_template_and_no_overwrite_prompt():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'function Get-ConfigSeedPath' in text
    assert 'config.seed.json' in text
    assert 'config.json (seed template)' in text
    assert 'Overwrite existing files for update?' not in text
    assert 'No deployed engine root found in shared_roots -- hooks not installed. Deploy engine first.' in text
