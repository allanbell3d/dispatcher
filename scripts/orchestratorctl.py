#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import subprocess

SCRIPTS_DIR = Path(__file__).resolve().parent


def current_task_id(data: dict) -> str:
    return str(data.get("task_id") or data.get("id") or "").strip()

def run(script: str, extra: list[str]) -> int:
    cmd = [sys.executable, str(SCRIPTS_DIR / script), *extra]
    return subprocess.call(cmd)

def cmd_toggle_hook(project_path, hook_name: str, enable: bool) -> int:
    from lib.common import (
        audit_log,
        load_project_config,
        resolve_path,
        resolve_project_root,
    )
    project_root = resolve_project_root(project_path)
    config = load_project_config(project_root)
    flags_dir = resolve_path("runtime_flags", project_root, config)
    hook_flags_dir = flags_dir / "hooks"
    hook_flags_dir.mkdir(parents=True, exist_ok=True)
    flag = hook_flags_dir / f"{hook_name}.disabled"

    if enable:
        flag.unlink(missing_ok=True)
        audit_log("hook_enabled", project_root=project_root, config=config, hook=hook_name)
        print(f"Hook '{hook_name}' enabled")
    else:
        flag.write_text(f"disabled by operator\n", encoding="utf-8")
        audit_log("hook_disabled", project_root=project_root, config=config, hook=hook_name)
        print(f"Hook '{hook_name}' disabled")
    return 0


def cmd_override(project_path, task_id: str, verdict: str, reason: str) -> int:
    from lib.common import (
        audit_log,
        load_project_config,
        resolve_path,
        resolve_project_root,
        timestamp,
        write_json,
    )
    project_root = resolve_project_root(project_path)
    config = load_project_config(project_root)
    merged_dir = resolve_path("merged_verdicts", project_root, config)
    merged_dir.mkdir(parents=True, exist_ok=True)
    verdict_data = {
        "task_id": task_id,
        "verdict": verdict,
        "consensus_rule": "manual_override",
        "override": True,
        "by": "operator",
        "reason": reason or f"manual override by operator",
        "verdicts": {},
        "dissent": [],
        "ts": timestamp(config),
    }
    write_json(merged_dir / f"{task_id}.json", verdict_data)
    audit_log("manual_override", project_root=project_root, config=config,
              task_id=task_id, verdict=verdict, reason=reason)
    print(f"Override written: {task_id} -> {verdict}")
    return 0


def cmd_resume(project_path, agent_name: str, refan: bool = False) -> int:
    from lib.common import (
        atomic_write,
        audit_log,
        clear_halt,
        is_halted,
        load_project_config,
        resolve_path,
        resolve_project_root,
    )
    project_root = resolve_project_root(project_path)
    config = load_project_config(project_root)
    halted, reason = is_halted(agent_name, project_root, config)
    if halted:
        clear_halt(agent_name, project_root, config)
        audit_log("manual_resume", project_root=project_root, config=config,
                  agent=agent_name, previous_reason=reason)
        print(f"Resumed agent '{agent_name}' (was halted: {reason})")
    else:
        print(f"Agent '{agent_name}' is not halted -- nothing to do")

    if refan:
        dispatch_dir = resolve_path("dispatch_root", project_root, config)
        task_id = ""
        try:
            from lib.common import read_json, resolve_path as rp
            ct = read_json(rp("current_task", project_root, config), {})
            task_id = current_task_id(ct)
        except Exception:
            pass
        if not task_id:
            print("No current task_id available -- skipping re-fan-out")
            return 0
        reviewers = config.get("gate", {}).get("require_approvals_from", [])
        for reviewer in reviewers:
            inbox = dispatch_dir / reviewer / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            msg = (
                f"FROM: orchestratorctl\n"
                f"TO: {reviewer}\n"
                f"TYPE: review_request\n"
                f"TASK_ID: {task_id}\n"
                f"---\n"
                f"Resume: please re-review task {task_id}."
            )
            msg_file = inbox / f"resume_{task_id}_{reviewer}.md"
            atomic_write(msg_file, msg)
        print(f"Re-fanned to {len(reviewers)} reviewers: {', '.join(reviewers)}")

    return 0


def cmd_status(project_path) -> int:
    from lib.common import (
        agent_names as get_agent_names,
        is_halted,
        load_project_config,
        read_json,
        resolve_path,
        resolve_project_root,
    )
    project_root = resolve_project_root(project_path)
    config = load_project_config(project_root)
    agents = get_agent_names(config)
    dispatch_root = resolve_path("dispatch_root", project_root, config)

    print(f"Project: {config.get('project', '?')}")
    print(f"Root:    {project_root}")
    print()

    # Current task
    try:
        ct = read_json(resolve_path("current_task", project_root, config), {})
        task_id = current_task_id(ct) or "(none)"
        task_title = ct.get("title", "")
        print(f"Current task: {task_id}" + (f" -- {task_title}" if task_title else ""))
    except Exception:
        print("Current task: (unreadable)")
    print()

    # Watcher
    stop_file = resolve_path("runtime_flags", project_root, config) / "STOP"
    watcher_log = resolve_path("logs", project_root, config) / "watcher.log"
    watcher_status = "STOPPED" if stop_file.exists() else ("RUNNING" if watcher_log.exists() else "UNKNOWN")
    print(f"Watcher: {watcher_status}")
    print()

    # Agent table
    print(f"{'Agent':<20} {'State':<12} {'Inbox':<8} {'Outbox':<8}")
    print("-" * 52)
    for agent in agents:
        halted, reason = is_halted(agent, project_root, config)
        inbox_dir = dispatch_root / agent / "inbox"
        outbox_dir = dispatch_root / agent / "outbox"
        try:
            inbox_count = len([p for p in inbox_dir.iterdir() if p.is_file() and p.suffix != ".tmp"]) if inbox_dir.is_dir() else 0
        except OSError:
            inbox_count = 0
        try:
            outbox_count = len([p for p in outbox_dir.iterdir() if p.is_file()]) if outbox_dir.is_dir() else 0
        except OSError:
            outbox_count = 0

        state = "HALTED" if halted else "active"
        print(f"{agent:<20} {state:<12} {inbox_count:<8} {outbox_count:<8}")
        if halted and reason:
            print(f"  halt reason: {reason}")

    # Fan-in trackers
    try:
        trackers = read_json(resolve_path("trackers", project_root, config), {})
        if trackers:
            print()
            print("Fan-in trackers:")
            for tid, t in trackers.items():
                received = list((t.get("received") or {}).keys())
                required = t.get("required", [])
                missing = sorted(set(required) - set(received))
                print(f"  {tid}: received={received} missing={missing}")
    except Exception:
        pass

    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Helper wrapper for common orchestrator commands")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ["doctor", "validate", "smoke"]:
        p = sub.add_parser(name)
        p.add_argument("project", nargs="?", default=None)

    p = sub.add_parser("send")
    p.add_argument("project")
    p.add_argument("recipient")
    p.add_argument("message", nargs="+")
    p.add_argument("--type", default="direct_message")
    p.add_argument("--task-id", default="")

    p = sub.add_parser("render-hooks")
    p.add_argument("project")
    p.add_argument("--agent", required=True)
    p.add_argument("--output", default="")

    # MCP frozen (spec rule #20) — re-enable when MCP is wired
    # p = sub.add_parser("render-mcp")
    # p.add_argument("project")
    # p.add_argument("--agent", required=True)

    p = sub.add_parser("paths")
    p.add_argument("project", nargs="?", default=None)

    p = sub.add_parser("install-hooks")
    p.add_argument("project", nargs="?", default=None)
    p.add_argument("--agent", default="")

    p = sub.add_parser("status")
    p.add_argument("project", nargs="?", default=None)

    p = sub.add_parser("resume")
    p.add_argument("project", nargs="?", default=None)
    p.add_argument("--agent", required=True)
    p.add_argument("--refan", action="store_true", help="Re-fan-out review requests to reviewers")

    p = sub.add_parser("override")
    p.add_argument("project", nargs="?", default=None)
    p.add_argument("--task", required=True)
    p.add_argument("--verdict", required=True, choices=["approved", "rejected"])
    p.add_argument("--reason", default="")

    p = sub.add_parser("toggle-hook")
    p.add_argument("project", nargs="?", default=None)
    p.add_argument("--hook", required=True)
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--enable", action="store_true")
    grp.add_argument("--disable", action="store_true")

    args = parser.parse_args()

    if args.cmd == "doctor":
        return run("doctor.py", [args.project] if args.project else [])
    if args.cmd == "validate":
        return run("validate.py", [args.project] if args.project else [])
    if args.cmd == "smoke":
        return run("dispatch_contract_smoke.py", [args.project] if args.project else [])
    if args.cmd == "send":
        extra = [args.recipient, *args.message, "--project", args.project, "--type", args.type]
        if args.task_id:
            extra += ["--task-id", args.task_id]
        return run("send.py", extra)
    if args.cmd == "render-hooks":
        extra = ["--project", args.project, "--agent", args.agent]
        if args.output:
            extra += ["--output", args.output]
        return run("install_hooks.py", extra)
    # MCP frozen (spec rule #20) — re-enable when MCP is wired
    # if args.cmd == "render-mcp":
    #     return run("render_mcp_config.py", ["--project", args.project, "--agent", args.agent])
    if args.cmd == "status":
        return cmd_status(args.project)
    if args.cmd == "resume":
        return cmd_resume(args.project, args.agent, refan=args.refan)
    if args.cmd == "override":
        return cmd_override(args.project, args.task, args.verdict, args.reason)
    if args.cmd == "toggle-hook":
        return cmd_toggle_hook(args.project, args.hook, args.enable)
    if args.cmd == "install-hooks":
        extra = []
        if args.project:
            extra += ["--project", args.project]
        if args.agent:
            extra += ["--agent", args.agent]
        else:
            extra += ["--all"]
        return run("install_hooks.py", extra)
    if args.cmd == "paths":
        from lib.common import load_project_config, resolve_path, resolve_project_root, resolve_shared_roots
        project_root = resolve_project_root(args.project)
        config = load_project_config(project_root)
        orch_root, agents_root = resolve_shared_roots(config)
        print(f"project_root={project_root}")
        print(f"orchestrator_root={orch_root}")
        print(f"agents_root={agents_root}")
        print(f"dispatch_dir={resolve_path('dispatch_root', project_root, config)}")
        print(f"memory_dir={resolve_path('memory', project_root, config)}")
        print(f"docs_dir={resolve_path('docs', project_root, config)}")
        return 0
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
