#!/usr/bin/env python3
"""Launcher quick access should point audit access at the audit location."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_launcher_audit_log_folder_uses_audit_path_parent():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert 'Split-Path $AuditLogPath -Parent' in text
