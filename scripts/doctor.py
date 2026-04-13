#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import platform
import shutil
import sys

from lib.common import load_project_config, resolve_path, resolve_project_root, resolve_shared_roots

def status(label: str, ok: bool, detail: str):
    mark = "OK" if ok else "FAIL"
    print(f"{mark:4} {label:24} {detail}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Probe orchestrator prerequisites")
    parser.add_argument("project", nargs="?", default=None)
    args = parser.parse_args()

    project_root = resolve_project_root(args.project)
    config = load_project_config(project_root)
    orchestrator_root, agents_root = resolve_shared_roots(config)

    failures = 0
    status("python", sys.version_info >= (3, 10), sys.version.split()[0])
    if sys.version_info < (3, 10):
        failures += 1

    dispatch_dir = resolve_path("dispatch_root", project_root, config)
    memories_dir = (project_root / config.get("paths", {}).get("memories_dir", "memories")).resolve()
    for label, path in [("project_root", project_root), ("dispatch_dir", dispatch_dir), ("memories_dir", memories_dir), ("orchestrator_root", orchestrator_root), ("agents_root", agents_root)]:
        ok = path.exists()
        status(label, ok, str(path))
        failures += 0 if ok else 1

    mux = shutil.which("psmux") or shutil.which("tmux")
    status("terminal mux", bool(mux), mux or "not found")
    status("bun", bool(shutil.which("bun")), shutil.which("bun") or "not found")
    status("node", bool(shutil.which("node")), shutil.which("node") or "not found")
    status("platform", True, platform.platform())

    logs_dir = resolve_path("logs", project_root, config)
    runtime_dir = resolve_path("runtime_flags", project_root, config)
    approvals_dir = (project_root / config.get("paths", {}).get("approvals_dir", ".orchestrator/approvals")).resolve()
    for label, path in [("logs_dir", logs_dir), ("runtime_dir", runtime_dir), ("approvals_dir", approvals_dir)]:
        try:
            path.mkdir(parents=True, exist_ok=True)
            test = path / ".write-test"
            test.write_text("ok\n", encoding="utf-8")
            test.unlink()
            ok = True
        except OSError:
            ok = False
        status(f"writable:{label}", ok, str(path))
        failures += 0 if ok else 1

    # decision_trace writable
    try:
        dt_path = resolve_path("decision_trace", project_root, config)
        dt_path.parent.mkdir(parents=True, exist_ok=True)
        test_dt = dt_path.parent / ".write-test-dt"
        test_dt.write_text("ok\n", encoding="utf-8")
        test_dt.unlink()
        ok = True
    except Exception:
        ok = False
    status("writable:decision_trace", ok, str(dt_path) if ok else "failed")
    failures += 0 if ok else 1

    # All 8 hook files exist
    hook_names = [
        "dispatch_gate.py", "check_gate.py", "inbox_access_guard.py",
        "monitor_ingest.py", "activity_logger.py", "dispatch_next_bug.py",
        "on_file_message.py", "stop_notify.py",
    ]
    hooks_dir = orchestrator_root / "hooks"
    for hook_name in hook_names:
        hp = hooks_dir / hook_name
        ok = hp.is_file()
        status(f"hook:{hook_name}", ok, str(hp))
        failures += 0 if ok else 1

    # sprint_profiles directory
    sp_dir = orchestrator_root / "sprint_profiles"
    ok = sp_dir.is_dir()
    status("sprint_profiles_dir", ok, str(sp_dir))
    # Not a failure -- advisory only

    # last_tool_use directory (created by liveness ticker)
    ltu_dir = resolve_path("state_root", project_root, config) / "last_tool_use"
    ok = ltu_dir.is_dir()
    status("last_tool_use_dir", ok, str(ltu_dir) + (" (will be created by watcher)" if not ok else ""))

    print("DONE")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
