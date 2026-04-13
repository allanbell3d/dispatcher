#!/usr/bin/env python3
"""Test F2: Watcher crash -> audit log + cc_all notification + exit 1.
Uses importlib to load watcher without package imports.
"""
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]

_CONFIG = {
    "project": "f2-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents"
    },
    "paths": {
        "state_root": ".orchestrator", "dispatch_root": "dispatch",
        "current_task": ".orchestrator/current_task.json",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts", "audit_log": ".orchestrator/audit.log",
        "trackers": ".orchestrator/trackers.json",
        "runtime_flags": ".orchestrator/runtime_flags", "logs": ".orchestrator/logs",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True},
        {"name": "gate-monitor-1", "executor": False},
    ],
    "gate": {"protected_branches": ["dev", "main"], "consensus_rule": "unanimous",
             "require_approvals_from": [], "max_rework_rounds": 3},
    "routing": {"cc_all": ["gate-monitor-1"], "escalation_target": "allan", "review_requests_to": []},
    "fan_in": {},
    "wake": {"mechanism": "tmux", "first_attempt_seconds": 999, "retry_interval_seconds": 999,
             "max_retries": 0, "monitor_pulse_seconds": 999},
    "session": {"require_ready_files": False, "session_prefix": "gate-"},
}

def check(label, condition, detail=""):
    ok = bool(condition)
    print(f"{'PASS' if ok else 'FAIL'}: {label}" + (f" ({detail})" if detail else ""))
    return ok

if __name__ == "__main__":
    passed = True
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
        (tmp / ".orchestrator/config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
        for agent in ["gate-ralph", "gate-monitor-1", "allan"]:
            for sub in ["inbox", "outbox", "reports", "done", "archive"]:
                (tmp / "dispatch" / agent / sub).mkdir(parents=True, exist_ok=True)
            (tmp / "dispatch" / agent / "ready").touch()

        # Harness: loads watcher via importlib (no package imports), patches two names,
        # then runs main(). sort_files_by_mtime raises on 2nd call -> triggers crash handler.
        harness = tmp / "crash_harness.py"
        harness.write_text(
            f"""\
import sys, pathlib, importlib.util

ROOT = pathlib.Path(r'{str(ROOT)}')
sys.path.insert(0, str(ROOT))

# Load watcher by file path — avoids package import requirement
_spec = importlib.util.spec_from_file_location(
    "watcher_mod", str(ROOT / "scripts" / "watcher.py")
)
watcher_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(watcher_mod)

# Patch in watcher_mod's own namespace (from-import binds there)
_orig_sort = watcher_mod.sort_files_by_mtime
_n = [0]
def _crash(paths):
    _n[0] += 1
    if _n[0] >= 2:
        raise RuntimeError("Simulated watcher crash — F2 test")
    return _orig_sort(paths)
watcher_mod.sort_files_by_mtime = _crash
watcher_mod.resolve_project_root = lambda *a, **kw: pathlib.Path(r'{str(tmp)}')

sys.exit(watcher_mod.main())
""",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(harness)],
            capture_output=True, text=True, timeout=15,
            cwd=str(tmp),
        )

        passed &= check("crash -> exit 1", result.returncode == 1,
                        f"exit={result.returncode}")

        audit_file = tmp / ".orchestrator/audit.log"
        passed &= check("audit.log created", audit_file.exists())
        if audit_file.exists():
            text = audit_file.read_text(encoding="utf-8")
            passed &= check("structured watcher_crash in audit log",
                            "watcher_crash" in text,
                            text[:300])

        monitor_inbox = tmp / "dispatch/gate-monitor-1/inbox"
        crash_files = list(monitor_inbox.glob("*.md")) if monitor_inbox.exists() else []
        passed &= check("monitor-1 notified of crash", len(crash_files) > 0,
                        f"{len(crash_files)} file(s)")

    sys.exit(0 if passed else 1)
