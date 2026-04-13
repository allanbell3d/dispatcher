#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> dispatcher/ (engine root, where lib/ lives)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json

from lib.common import ensure_dispatch_dirs, load_project_config, resolve_path, resolve_project_root

def hook_command(script_path: Path) -> str:
    return f'python "{script_path}"'

def command_hook(script_path: Path, *, async_: bool = False) -> dict:
    hook = {"type": "command", "command": hook_command(script_path)}
    if async_:
        hook["async"] = True
    return hook

def hook_entry(matcher: str, script_path: Path, *, if_clause: str = "", async_: bool = False) -> dict:
    entry = {
        "matcher": matcher,
        "hooks": [command_hook(script_path, async_=async_)],
    }
    if if_clause:
        entry["if"] = if_clause
    return entry

def build_hook_inventory(orchestrator_root, agent: str, config: dict) -> dict:
    hook_root = orchestrator_root / "hooks"
    is_executor = any(
        a.get("executor")
        for a in config.get("agents", [])
        if a.get("name") == agent
    )

    pre_tool_use = [
        hook_entry(
            "Write|Edit|MultiEdit|Bash|Glob|Grep|ListDir",
            hook_root / "dispatch_gate.py",
        ),
        hook_entry(
            "Read|Grep|Glob|Bash",
            hook_root / "inbox_access_guard.py",
        ),
    ]
    if is_executor:
        pre_tool_use.append(
            hook_entry(
                "Bash",
                hook_root / "check_gate.py",
                if_clause="Bash(git commit *)",
            )
        )

    post_tool_use = [
        hook_entry(
            "Write|Edit|MultiEdit|Bash|Read|Glob|Grep",
            hook_root / "activity_logger.py",
            async_=True,
        )
    ]
    if is_executor:
        post_tool_use.extend([
            hook_entry(
                "Bash|Write|Edit|MultiEdit|Read|Grep|Glob",
                hook_root / "monitor_ingest.py",
                async_=True,
            ),
            hook_entry(
                "Bash",
                hook_root / "dispatch_next_bug.py",
                if_clause="Bash(git commit *)",
            ),
        ])

    return {
        "hooks": {
            "FileChanged": [
                hook_entry("dispatch/*/inbox/*.md", hook_root / "on_file_message.py"),
                hook_entry("dispatch/*/inbox/*.json", hook_root / "on_file_message.py"),
            ],
            "PreToolUse": pre_tool_use,
            "PostToolUse": post_tool_use,
            "Stop": [
                {"hooks": [command_hook(hook_root / "stop_notify.py")]}
            ],
        }
    }

def _hook_key(event: str, entry) -> tuple[str, str, str] | None:
    if not isinstance(entry, dict):
        return None
    matcher = entry.get("matcher", "")
    if matcher is None:
        matcher = ""
    if not isinstance(matcher, str):
        return None
    hooks = entry.get("hooks") or []
    if len(hooks) != 1:
        return None
    hook = hooks[0]
    if not isinstance(hook, dict) or hook.get("type") != "command":
        return None
    command = hook.get("command")
    if not isinstance(command, str) or not command:
        return None
    return (event, matcher, command)

def reconcile_hook_entries(existing_entries, desired_entries, event: str) -> list:
    desired_by_key = {}
    desired_order = []
    for entry in desired_entries:
        key = _hook_key(event, entry)
        if key is None:
            desired_order.append((None, entry))
            continue
        if key not in desired_by_key:
            desired_order.append((key, entry))
        desired_by_key[key] = entry

    merged = []
    used_keys = set()
    for entry in existing_entries:
        key = _hook_key(event, entry)
        if key is not None and key in desired_by_key:
            if key in used_keys:
                continue
            merged.append(desired_by_key[key])
            used_keys.add(key)
            continue
        merged.append(entry)

    for key, entry in desired_order:
        if key is None:
            merged.append(entry)
        elif key not in used_keys:
            merged.append(entry)
            used_keys.add(key)
    return merged

def merge_settings(base: dict, update: dict) -> dict:
    result = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            if key == "hooks":
                merged_hooks = dict(result[key])
                for event, entries in value.items():
                    base_entries = merged_hooks.get(event, [])
                    merged_hooks[event] = reconcile_hook_entries(base_entries, entries, event)
                result[key] = merged_hooks
            else:
                result[key] = merge_settings(result[key], value)
        else:
            result[key] = value
    return result

def default_settings_path(project_root: Path) -> Path:
    return project_root / ".claude" / "settings.local.json"

def write_settings(target_path: Path, base: dict, update: dict) -> Path:
    merged = merge_settings(base, update)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return target_path

def load_existing_settings(target_path: Path) -> dict:
    if not target_path.exists():
        return {}
    try:
        return json.loads(target_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def main() -> int:
    parser = argparse.ArgumentParser(description="Render or install hook settings for an agent")
    parser.add_argument("--agent", default="")
    parser.add_argument("--all", action="store_true",
                        help="Install hooks for all agents in config")
    parser.add_argument("--project", default=None)
    parser.add_argument("--settings-file", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    project_root = resolve_project_root(args.project)
    config = load_project_config(project_root)
    orch_root = ROOT

    # Ensure project structure exists
    dispatch_dir = resolve_path("dispatch_root", project_root, config)
    for agent_cfg in config.get("agents", []):
        name = (agent_cfg.get("name") or "").strip()
        if name:
            ensure_dispatch_dirs(dispatch_dir, name)
    for key in ("plans", "tasks", "diffs", "merged_verdicts", "halts", "runtime_flags", "logs"):
        resolve_path(key, project_root, config).mkdir(parents=True, exist_ok=True)

    def install_for(agent_name: str, target_str: str = "") -> str:
        data = build_hook_inventory(orch_root, agent_name, config)
        target = target_str or args.output or args.settings_file
        if target:
            target_path = Path(target)
            existing = load_existing_settings(target_path)
            write_settings(target_path, existing, data)
            return str(target_path)
        return json.dumps(data, indent=2)

    if args.all:
        target_path = Path(args.output or args.settings_file) if (args.output or args.settings_file) else default_settings_path(project_root)
        merged = load_existing_settings(target_path)
        for agent_cfg in config.get("agents", []):
            agent_name = (agent_cfg.get("name") or "").strip()
            if not agent_name:
                continue
            merged = merge_settings(merged, build_hook_inventory(orch_root, agent_name, config))
        write_settings(target_path, {}, merged)
        print(f"written to {target_path}")
        print(f"merged hooks for {sum(1 for a in config.get('agents', []) if (a.get('name') or '').strip())} agents")
        return 0

    if not args.agent:
        parser.error("--agent is required unless --all is specified")

    print(install_for(args.agent))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
