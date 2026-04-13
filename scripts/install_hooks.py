#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> dispatcher/ (engine root, where lib/ lives)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json

from lib.common import ensure_dispatch_dirs, load_project_config, resolve_path, resolve_project_root, resolve_shared_roots

def hook_command(script_path: Path) -> str:
    return f'python "{script_path}"'

def build_hooks(orchestrator_root, agent: str, config: dict) -> dict:
    # Rule 17 exception: dispatch_gate must be first in PreToolUse ordering.
    # Current structure has no dispatch_gate entry — requires structural rearrangement.
    hook_root = orchestrator_root / "hooks"
    inbox_match = f"dispatch/{agent}/inbox/*.md"
    is_executor = any(
        a.get("executor")
        for a in config.get("agents", [])
        if a.get("name") == agent
    )

    pre_tool_use = [
        {
            "matcher": "Write|Edit|MultiEdit|Bash|Glob|Grep|ListDir",
            "hooks": [{"type": "command", "command": hook_command(hook_root / "dispatch_gate.py")}],
        },
        {
            "matcher": "Read|Grep|Glob|Bash",
            "hooks": [{"type": "command", "command": hook_command(hook_root / "inbox_access_guard.py")}],
        },
    ]
    if is_executor:
        pre_tool_use.append({
            "matcher": "Bash",
            "if": "Bash(git commit *)",
            "hooks": [{"type": "command", "command": hook_command(hook_root / "check_gate.py")}],
        })

    post_tool_use = [
        {
            "matcher": "Write|Edit|MultiEdit|Bash|Read|Glob|Grep",
            "hooks": [{"type": "command", "command": hook_command(hook_root / "activity_logger.py"),
                       "async": True}],
        }
    ]
    if is_executor:
        post_tool_use.extend([
            {
                "matcher": "Bash|Write|Edit|MultiEdit|Read|Grep|Glob",
                "hooks": [{"type": "command", "command": hook_command(hook_root / "monitor_ingest.py"),
                           "async": True}],
            },
            {
                "matcher": "Bash",
                "if": "Bash(git commit *)",
                "hooks": [{"type": "command", "command": hook_command(hook_root / "dispatch_next_bug.py")}],
            },
        ])

    return {
        "hooks": {
            "FileChanged": [
                {
                    "matcher": inbox_match,
                    "hooks": [{"type": "command",
                               "command": hook_command(hook_root / "on_file_message.py")}],
                }
            ],
            "PreToolUse": pre_tool_use,
            "PostToolUse": post_tool_use,
            "Stop": [
                {"hooks": [{"type": "command",
                            "command": hook_command(hook_root / "stop_notify.py")}]}
            ],
        }
    }

def deep_merge(base: dict, update: dict) -> dict:
    result = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            # Dedup hook entries by command string to prevent doubling on re-run.
            existing_cmds = {
                h.get("command", "")
                for entry in result[key]
                if isinstance(entry, dict)
                for h in (entry.get("hooks") or [])
                if isinstance(h, dict)
            }
            deduped = []
            for item in value:
                if not isinstance(item, dict):
                    deduped.append(item)
                    continue
                item_cmds = {h.get("command", "") for h in (item.get("hooks") or []) if isinstance(h, dict)}
                if not item_cmds or not item_cmds.intersection(existing_cmds):
                    deduped.append(item)
                    existing_cmds.update(item_cmds)
            result[key] = result[key] + deduped
        else:
            result[key] = value
    return result

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
    orch_root, _ = resolve_shared_roots(config)

    # Ensure project structure exists
    dispatch_dir = resolve_path("dispatch_root", project_root, config)
    for agent_cfg in config.get("agents", []):
        name = (agent_cfg.get("name") or "").strip()
        if name:
            ensure_dispatch_dirs(dispatch_dir, name)
    for key in ("plans", "tasks", "diffs", "merged_verdicts", "halts", "runtime_flags", "logs"):
        resolve_path(key, project_root, config).mkdir(parents=True, exist_ok=True)

    def install_for(agent_name: str, target_str: str = "") -> str:
        data = build_hooks(orch_root, agent_name, config)
        target = target_str or args.output or args.settings_file
        if target:
            target_path = Path(target)
            if target_path.exists():
                try:
                    existing = json.loads(target_path.read_text(encoding="utf-8"))
                except Exception:
                    existing = {}
                merged = deep_merge(existing, data)
            else:
                merged = data
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
            return str(target_path)
        return json.dumps(data, indent=2)

    if args.all:
        for agent_cfg in config.get("agents", []):
            agent_name = (agent_cfg.get("name") or "").strip()
            if not agent_name:
                continue
            settings_file = str(agent_cfg.get("settings_file", ""))
            result = install_for(agent_name, settings_file)
            if settings_file:
                print(f"{agent_name}: written to {result}")
            else:
                print(f"--- {agent_name} ---")
                print(result)
        return 0

    if not args.agent:
        parser.error("--agent is required unless --all is specified")

    print(install_for(args.agent))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
