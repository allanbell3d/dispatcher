#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json

from lib.common import load_project_config, resolve_project_root, resolve_shared_roots

def main() -> int:
    parser = argparse.ArgumentParser(description="Render MCP config for a specific agent")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--project", default=None)
    args = parser.parse_args()

    project_root = resolve_project_root(args.project)
    config = load_project_config(project_root)
    orch_root, _ = resolve_shared_roots(config)

    payload = {
        "command": "bun",
        "args": [str(orch_root / "mcp-server" / "server.ts")],
        "env": {
            "AGENT_NAME": args.agent,
            "PROJECT_ROOT": str(project_root),
        }
    }
    print(json.dumps(payload, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
