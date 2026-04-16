#!/usr/bin/env python3
"""Smoke tests for the dispatcher desktop shell."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from desktop_app.ui import create_window  # noqa: E402


def test_desktop_window_builds_tabs():
    app = QApplication.instance() or QApplication([])
    window = create_window()
    try:
        labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        assert labels == ["Dashboard", "Sprint", "Agents", "Tasks", "Hooks", "Logs", "Settings"]
    finally:
        window.close()
