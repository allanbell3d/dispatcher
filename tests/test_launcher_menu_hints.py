#!/usr/bin/env python3
"""Launcher menu regressions: mandatory hint parameters must be supplied."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "orch_launcher.ps1"


def test_all_read_checkbox_menu_calls_supply_hint():
    text = LAUNCHER.read_text(encoding="utf-8")
    lines = text.splitlines()
    offenders = []
    for idx, line in enumerate(lines):
        if "Read-CheckboxMenu" not in line:
            continue
        stripped = line.strip()
        if stripped.startswith("function Read-CheckboxMenu"):
            continue
        if '"Read-CheckboxMenu"' in stripped:
            continue
        window = " ".join(lines[idx:idx + 4])
        if "-Hint" not in window:
            offenders.append(idx + 1)
    assert offenders == [], f"Read-CheckboxMenu missing -Hint near lines: {offenders}"
