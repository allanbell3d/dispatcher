#!/usr/bin/env python3
"""Presence checks for newly installed coordinated Codex reviewer profiles."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_codex_reviewer_profile_files_exist():
    expected = [
        ROOT / "agents/profiles/coordinated/gate-codex-architect/CLAUDE.md",
        ROOT / "agents/profiles/coordinated/gate-codex-architect/role_prompt.md",
        ROOT / "agents/profiles/coordinated/gate-codex-critic/CLAUDE.md",
        ROOT / "agents/profiles/coordinated/gate-codex-critic/role_prompt.md",
        ROOT / "memory/gate-codex-architect/CLAUDE.md",
        ROOT / "memory/gate-codex-architect/notes.md",
        ROOT / "memory/gate-codex-architect/startup_protocol.md",
        ROOT / "memory/gate-codex-critic/CLAUDE.md",
        ROOT / "memory/gate-codex-critic/notes.md",
        ROOT / "memory/gate-codex-critic/startup_protocol.md",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    assert missing == []
