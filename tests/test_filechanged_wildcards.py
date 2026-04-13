#!/usr/bin/env python3
"""Path-shape proof for the reduced FileChanged wildcard matchers."""

from pathlib import PurePosixPath


MATCH_MD = "dispatch/*/inbox/*.md"
MATCH_JSON = "dispatch/*/inbox/*.json"
MATCH_ANY = "dispatch/*/inbox/*.*"


def test_markdown_wildcard_matches_any_agent_inbox_markdown_file():
    assert PurePosixPath("dispatch/gate-critic/inbox/review.md").match(MATCH_MD)
    assert PurePosixPath("dispatch/gate-codex-architect/inbox/request.md").match(MATCH_MD)


def test_json_wildcard_matches_any_agent_inbox_json_file():
    assert PurePosixPath("dispatch/gate-monitor/inbox/tool-summary.json").match(MATCH_JSON)
    assert PurePosixPath("dispatch/gate-codex-critic/inbox/review.json").match(MATCH_JSON)


def test_combined_wildcard_shape_covers_both_suffixes_but_not_wrong_folders():
    assert PurePosixPath("dispatch/gate-monitor/inbox/tool-summary.json").match(MATCH_ANY)
    assert PurePosixPath("dispatch/gate-critic/inbox/review.md").match(MATCH_ANY)
    assert not PurePosixPath("dispatch/gate-critic/outbox/review.md").match(MATCH_MD)
    assert not PurePosixPath("dispatch/gate-critic/inbox/review.tmp").match(MATCH_JSON)
