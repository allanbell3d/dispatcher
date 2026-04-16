#!/usr/bin/env python3
"""Launcher should guard Count usage against single-object PowerShell returns."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_wraps_where_object_and_get_childitem_counts():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert '@($results | Where-Object { $_.ready }).Count' in text
    assert '@(Get-ChildItem -LiteralPath $inboxPath -File -ErrorAction SilentlyContinue).Count' in text
