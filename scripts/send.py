#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import argparse
import json
import os

from lib.common import (
    atomic_write,
    compute_message_name,
    ensure_dispatch_dirs,
    load_project_config,
    resolve_path,
    resolve_project_root,
    timestamp,
)

def canonical_message(config: dict, sender: str, recipient: str, body: str, msg_type: str, task_id: str = "", verdict: str = "") -> str:
    lines = [
        f"FROM: {sender}",
        f"TO: {recipient}",
        f"TYPE: {msg_type}",
    ]
    if task_id:
        lines.append(f"TASK_ID: {task_id}")
    if verdict:
        lines.append(f"VERDICT: {verdict}")
    lines.append(f"TIMESTAMP: {timestamp(config)}")
    lines.extend(["---", body.strip(), ""])
    return "\n".join(lines)

def parse_args():
    p = argparse.ArgumentParser(description="Queue a dispatch message")
    p.add_argument("recipient")
    p.add_argument("message", nargs="*", help="message body")
    p.add_argument("--project", dest="project", default=None)
    p.add_argument("--type", dest="msg_type", default="direct_message")
    p.add_argument("--task-id", default="")
    p.add_argument("--verdict", default="")
    p.add_argument("--file", dest="file_path", default="")
    p.add_argument("--activity", action="store_true")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    project_root = resolve_project_root(args.project)
    config = load_project_config(project_root)
    dispatch_dir = resolve_path("dispatch_root", project_root, config)
    sender = os.environ.get("GATE_AGENT_NAME", "system").strip() or "system"
    ensure_dispatch_dirs(dispatch_dir, sender)

    escalation_target = config.get("routing", {}).get("escalation_target", "")
    valid = set([*([escalation_target] if escalation_target else []), *[a["name"] for a in config.get("agents", []) if a.get("name")]])
    if args.recipient not in valid:
        print(json.dumps({"error": f"Unknown recipient {args.recipient}", "valid": sorted(valid)}))
        return 1

    if args.activity:
        stdin_text = sys.stdin.read().strip()
        try:
            payload = json.loads(stdin_text) if stdin_text else {}
        except json.JSONDecodeError:
            payload = {"raw": stdin_text}
        tool_name = payload.get("tool_name") or payload.get("tool") or "activity"
        tool_input = payload.get("tool_input") or payload.get("input") or {}
        detail = tool_input.get("file_path") or tool_input.get("command") or tool_input.get("path") or payload.get("raw", "")
        body = f"{tool_name}: {detail}".strip()
        msg_type = "activity"
    elif args.file_path:
        try:
            body = Path(args.file_path).read_text(encoding="utf-8")
        except OSError as exc:
            body = f"ERROR reading {args.file_path}: {exc}"
        msg_type = args.msg_type
    else:
        body = " ".join(args.message).strip()
        msg_type = args.msg_type

    out_file = dispatch_dir / sender / "outbox" / compute_message_name(f"to-{args.recipient}", args.task_id or args.recipient, config)
    atomic_write(out_file, canonical_message(config, sender, args.recipient, body, msg_type, args.task_id, args.verdict))
    print(json.dumps({"queued": True, "path": str(out_file), "from": sender, "to": args.recipient}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
