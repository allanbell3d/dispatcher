#!/usr/bin/env python3
"""Launcher main loop should use hashtable-safe nav-state access."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_uses_index_access_for_nav_state():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert '(Cur)["id"]' in text
    assert '$s["header"]' in text
    assert '$s["hint"]' in text
    assert '$s["items"]' in text
    assert '$s["selPos"]' in text
    assert '(Cur)["items"] = Build-MainMenu' in text
