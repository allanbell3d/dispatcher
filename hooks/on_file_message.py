#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import os
import time as _time

from lib.common import trace_hook

def extract_path(stdin_text: str) -> Path | None:
    if not stdin_text.strip():
        return None
    try:
        payload = json.loads(stdin_text)
    except json.JSONDecodeError:
        return None
    for key in ("file_path", "path"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return Path(value)
    changed = payload.get("changed_files") or payload.get("files")
    if isinstance(changed, list):
        for item in changed:
            if isinstance(item, str) and item:
                return Path(item)
            if isinstance(item, dict):
                value = item.get("path") or item.get("file_path")
                if value:
                    return Path(str(value))
    return None

def move_to_done(path: Path):
    if path.parent.name != "inbox":
        return
    done_dir = path.parent.parent / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    target = done_dir / path.name
    if target.exists():
        target = done_dir / f"{path.stem}-consumed{path.suffix}"
    os.replace(str(path), str(target))

def main() -> int:
    # P3 exemption: this hook fires for ALL sessions (including non-orchestrator)
    # because dispatch injection is useful universally — Allan's own sessions
    # benefit from inbox message injection. Unlike enforcement hooks, this is
    # advisory (exit 0 always, never blocks). Skipping GATE_AGENT_NAME check
    # is intentional. See critic reviews m7 / run02 m-3.
    from lib.common import is_hook_disabled
    if is_hook_disabled("on_file_message"):
        sys.exit(0)

    _t0 = _time.monotonic()
    agent = os.environ.get("GATE_AGENT_NAME", "")
    stdin_text = sys.stdin.read()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else extract_path(stdin_text)
    if not path or not path.exists() or not path.is_file():
        trace_hook(hook="on_file_message", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="no valid file path")
        print(json.dumps({}))
        return 0
    try:
        content = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        trace_hook(hook="on_file_message", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="file read error")
        print(json.dumps({}))
        return 0
    move_to_done(path)
    if not content:
        trace_hook(hook="on_file_message", agent=agent,
                   decision="skip", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="empty content")
        print(json.dumps({}))
        return 0
    trace_hook(hook="on_file_message", agent=agent,
               decision="inject", elapsed_ms=(_time.monotonic() - _t0) * 1000,
               file=str(path))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": f"NEW DISPATCH MESSAGE from {path.name}:\n\n{content}"}}))
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # P4: advisory — fail-open
