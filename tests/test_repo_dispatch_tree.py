#!/usr/bin/env python3
"""Checked-in repo dispatch tree should satisfy validator folder expectations."""

from pathlib import Path

from lib.common import agent_names, load_project_config


ROOT = Path(__file__).resolve().parents[1]


def test_repo_dispatch_tree_has_required_agent_subfolders():
    config = load_project_config(ROOT)
    dispatch_root = ROOT / "dispatch"

    missing: list[str] = []
    for agent in agent_names(config):
        for subdir in ("inbox", "outbox", "reports", "done", "archive"):
            path = dispatch_root / agent / subdir
            if not path.exists():
                missing.append(f"dispatch/{agent}/{subdir}")

    assert not missing, f"missing dispatch subfolders: {missing}"


def test_repo_dispatch_tree_contains_only_placeholder_files():
    dispatch_root = ROOT / "dispatch"
    unexpected = []

    for path in dispatch_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".gitkeep":
            continue
        unexpected.append(str(path.relative_to(ROOT)))

    assert not unexpected, f"unexpected checked-in dispatch artifacts: {unexpected}"


def test_repo_has_no_checked_in_halt_flags():
    halts_dir = ROOT / ".orchestrator" / "halts"
    unexpected = []
    if halts_dir.exists():
        unexpected = [str(path.relative_to(ROOT)) for path in halts_dir.glob("*.flag")]

    assert not unexpected, f"unexpected checked-in halt flags: {unexpected}"
