#!/usr/bin/env python3
"""Installer tests for scripts/install_hooks.py."""

import importlib.util
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_hooks.py"

_CONFIG = {
    "project": "c3-test",
    "shared_roots": {
        "orchestrator_primary": str(ROOT),
        "orchestrator_fallback": str(ROOT),
        "agents_primary": str(ROOT),
        "agents_fallback": str(ROOT),
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "plans": ".orchestrator/plans",
        "tasks": ".orchestrator/tasks",
        "diffs": ".orchestrator/diffs",
        "current_task": ".orchestrator/current_task.json",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "audit_log": ".orchestrator/audit.log",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True, "roles": ["coder"]},
        {"name": "gate-architect", "executor": False, "roles": ["reviewer"]},
    ],
    "gate": {
        "protected_branches": ["dev", "main"],
        "consensus_rule": "unanimous",
        "require_approvals_from": ["gate-architect"],
        "max_rework_rounds": 3,
    },
    "routing": {"cc_all": [], "escalation_target": "allan"},
    "fan_in": {},
    "wake": {},
    "session": {},
}


def _config_with_shared_root(shared_root: str) -> dict:
    data = json.loads(json.dumps(_CONFIG))
    data["shared_roots"]["orchestrator_primary"] = shared_root
    data["shared_roots"]["orchestrator_fallback"] = shared_root
    return data


def load_module():
    spec = importlib.util.spec_from_file_location("install_hooks_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_install(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(project), *extra],
        capture_output=True,
        text=True,
        cwd=str(project),
    )


def write_config(project: Path) -> None:
    (project / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (project / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")


def make_project_dir() -> Path:
    base = ROOT / ".tmp_install_hooks_tests"
    project = base / f"c3_{uuid.uuid4().hex}"
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    project.mkdir(parents=True, exist_ok=True)
    return project


def test_inventory_includes_both_inbox_suffixes_and_executor_hooks():
    mod = load_module()
    inventory_exec = mod.build_hook_inventory(ROOT, "gate-ralph", _CONFIG)
    file_changed = inventory_exec["hooks"]["FileChanged"]
    matchers = [entry["matcher"] for entry in file_changed]

    assert "dispatch/*/inbox/*.md" in matchers
    assert "dispatch/*/inbox/*.json" in matchers

    pre_tool_use = inventory_exec["hooks"]["PreToolUse"]
    post_tool_use = inventory_exec["hooks"]["PostToolUse"]
    assert any("check_gate" in hook["command"] for entry in pre_tool_use for hook in entry["hooks"])
    assert any("monitor_ingest" in hook["command"] for entry in post_tool_use for hook in entry["hooks"])

    inventory_non_exec = mod.build_hook_inventory(ROOT, "gate-architect", _CONFIG)
    non_exec_pre = inventory_non_exec["hooks"]["PreToolUse"]
    non_exec_post = inventory_non_exec["hooks"]["PostToolUse"]
    assert not any("check_gate" in hook["command"] for entry in non_exec_pre for hook in entry["hooks"])
    assert any("monitor_ingest" in hook["command"] for entry in non_exec_post for hook in entry["hooks"])


def test_inventory_prefers_configured_shared_engine_root_for_hook_commands():
    mod = load_module()
    config = _config_with_shared_root("W:/Claude_Library/orchestrator")

    inventory = mod.build_hook_inventory(ROOT, "gate-ralph", config)

    commands = [
        hook["command"]
        for entries in inventory["hooks"].values()
        for entry in entries
        for hook in entry.get("hooks", [])
    ]

    assert any('python "W:\\Claude_Library\\orchestrator\\hooks\\dispatch_gate.py"' == cmd for cmd in commands)
    assert any('python "W:\\Claude_Library\\orchestrator\\hooks\\stop_notify.py"' == cmd for cmd in commands)
    assert not any(str(ROOT / "hooks" / "dispatch_gate.py") in cmd for cmd in commands)


def test_merge_settings_reconciles_by_event_matcher_and_command():
    mod = load_module()
    desired = mod.build_hook_inventory(ROOT, "gate-ralph", _CONFIG)
    dispatch_cmd = desired["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    dispatch_matcher = desired["hooks"]["PreToolUse"][0]["matcher"]
    other_command = "python \"D:/elsewhere/other.py\""

    existing = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": dispatch_matcher,
                    "if": "Bash(old condition)",
                    "hooks": [{"type": "command", "command": dispatch_cmd}],
                },
                {
                    "matcher": "Read|Grep|Glob|Bash",
                    "hooks": [{"type": "command", "command": dispatch_cmd}],
                },
                {
                    "matcher": "Read",
                    "hooks": [{"type": "command", "command": other_command}],
                },
            ]
        }
    }

    merged = mod.merge_settings(existing, desired)
    pre_tool_use = merged["hooks"]["PreToolUse"]

    replaced_entries = [
        entry for entry in pre_tool_use
        if entry.get("matcher") == dispatch_matcher
        and entry.get("hooks", [{}])[0].get("command") == dispatch_cmd
    ]
    assert len(replaced_entries) == 1
    assert "if" not in replaced_entries[0]

    preserved_entries = [
        entry for entry in pre_tool_use
        if entry.get("matcher") == "Read|Grep|Glob|Bash"
        and entry.get("hooks", [{}])[0].get("command") == dispatch_cmd
    ]
    assert len(preserved_entries) == 1

    assert any(
        entry.get("matcher") == "Read"
        and entry.get("hooks", [{}])[0].get("command") == other_command
        for entry in pre_tool_use
    )


def test_all_writes_shared_settings_local_json_by_default():
    project = make_project_dir()
    try:
        write_config(project)

        existing = project / ".claude" / "settings.local.json"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Read",
                                "hooks": [{"type": "command", "command": "existing-hook"}],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        result = run_install(project, "--all")
        assert result.returncode == 0, result.stderr

        settings_path = project / ".claude" / "settings.local.json"
        assert settings_path.exists()

        data = json.loads(settings_path.read_text(encoding="utf-8"))
        first_snapshot = json.dumps(data, sort_keys=True)
        pre_tool_use = data["hooks"]["PreToolUse"]
        assert any(
            entry.get("matcher") == "Read"
            and entry.get("hooks", [{}])[0].get("command") == "existing-hook"
            for entry in pre_tool_use
        )
        assert any(
            entry.get("matcher") == "dispatch/*/inbox/*.md"
            for entry in data["hooks"]["FileChanged"]
        )
        assert any(
            entry.get("matcher") == "dispatch/*/inbox/*.json"
            for entry in data["hooks"]["FileChanged"]
        )
        assert "written to" in result.stdout
        assert "merged hooks for 2 agents" in result.stdout

        rerun = run_install(project, "--all")
        assert rerun.returncode == 0, rerun.stderr
        second_snapshot = json.dumps(
            json.loads(settings_path.read_text(encoding="utf-8")),
            sort_keys=True,
        )
        assert second_snapshot == first_snapshot
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_single_agent_rendering_stays_json_and_does_not_write_settings_file():
    project = make_project_dir()
    try:
        write_config(project)

        result = run_install(project, "--agent", "gate-architect")
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)

        assert "hooks" in data
        assert not (project / ".claude" / "settings.local.json").exists()
    finally:
        shutil.rmtree(project, ignore_errors=True)
