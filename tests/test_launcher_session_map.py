#!/usr/bin/env python3
"""Launcher should persist edited session names and avoid double-prefix defaults."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_persists_session_name_map_and_uses_default_helper():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'function Get-SessionMapPath' in text
    assert 'session_names.json' in text
    assert 'function Get-DefaultSessionName' in text
    assert 'if ($AgentName.StartsWith($prefix' in text
    assert 'Get-DefaultSessionName $a' in text
    assert 'Get-SessionNameForAgent $a' in text
