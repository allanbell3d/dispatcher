#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import subprocess
import tempfile
import time

# Inline config fixture — no Project_Template dependency
_INLINE_CONFIG = {
    "project": "smoke-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents"
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "plans": ".orchestrator/plans",
        "tasks": ".orchestrator/tasks",
        "current_task": ".orchestrator/tasks/current_task.json",
        "trackers": ".orchestrator/trackers.json",
        "diffs": ".orchestrator/diffs",
        "audit_log": ".orchestrator/audit.log",
        "decision_trace": ".orchestrator/logs/decision_trace.log",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "runtime_flags": ".orchestrator/runtime_flags",
        "playwright_tests": "tests/e2e",
        "logs": ".orchestrator/logs",
        "approvals_source": "outbox",
        "halt_mode": "flag_file"
    },
    "wake": {
        "mechanism": "tmux",
        "first_attempt_seconds": 2,
        "retry_interval_seconds": 30,
        "max_retries": 5,
        "monitor_pulse_seconds": 10,
        "idle_threshold_seconds": 120,
        "liveness_check_interval_seconds": 30
    },
    "session": {
        "require_ready_files": False,
        "halt_between_batches": False,
        "session_prefix": "gate-"
    },
    "agents": [
        {"name": "gate-ralph", "profile": "gate-ralph", "executor": True, "roles": ["coder"]},
        {"name": "gate-architect", "profile": "gate-architect", "executor": False, "roles": ["reviewer"]},
        {"name": "gate-monitor", "profile": "gate-monitor", "executor": False, "roles": ["monitor"]}
    ],
    "routing": {
        "cc_all": ["gate-monitor"],
        "review_requests_to": ["gate-architect"],
        "escalation_target": "allan"
    },
    "gate": {
        "require_approvals_from": ["gate-architect"],
        "consensus_rule": "unanimous",
        "max_rework_rounds": 3,
        "protected_branches": ["dev", "main"]
    },
    "fan_in": {
        "review": {
            "required": ["gate-architect"],
            "timeout_seconds": 1200,
            "on_timeout": "escalate_allan"
        }
    }
}


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def wait_for(glob_path: Path, timeout: float = 10.0) -> list[Path]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        matches = list(glob_path.parent.glob(glob_path.name))
        if matches:
            return matches
        time.sleep(0.2)
    return []


def build_fixture(root: Path) -> None:
    """Build a minimal project fixture inline — no Project_Template required."""
    cfg = _INLINE_CONFIG

    # Write config
    config_path = root / ".orchestrator" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    # Create dispatch dirs for each agent
    dispatch_root = root / cfg["paths"]["dispatch_root"]
    for agent in cfg["agents"]:
        name = agent["name"]
        for subdir in ("inbox", "outbox", "reports", "done", "archive"):
            (dispatch_root / name / subdir).mkdir(parents=True, exist_ok=True)

    # Create tasks and state dirs
    (root / ".orchestrator" / "tasks").mkdir(parents=True, exist_ok=True)
    (root / ".orchestrator" / "runtime_flags").mkdir(parents=True, exist_ok=True)


def main() -> int:
    tool_root = Path(__file__).resolve().parent.parent
    watcher = tool_root / "scripts" / "watcher.py"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "project"

        # Build fixture inline — no shutil.copytree from Project_Template
        build_fixture(root)

        # Load agent names from the inline fixture — must succeed or test fails
        cfg = json.loads((root / ".orchestrator" / "config.json").read_text(encoding="utf-8"))
        _agents = [a["name"] for a in cfg.get("agents", []) if a.get("name")]
        _coders = [a["name"] for a in cfg.get("agents", []) if a.get("executor")]
        _reviewers = [a["name"] for a in cfg.get("agents", []) if "reviewer" in (a.get("roles") or [])]

        if not _coders:
            raise RuntimeError("Fixture config has no executor agent")
        if not _reviewers:
            raise RuntimeError("Fixture config has no reviewer agents")

        proc = subprocess.Popen(
            [sys.executable, str(watcher), str(root)],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            _coder = _coders[0]
            _r0 = _reviewers[0]

            review = (
                f"FROM: {_coder}\n"
                f"TO: {_r0}\n"
                f"TYPE: review_request\n"
                f"TASK_ID: SMOKE-1\n"
                f"---\n"
                f"Review this diff.\n"
            )
            write(root / "dispatch" / _coder / "outbox" / "review.md", review)

            if not wait_for(root / "dispatch" / _r0 / "inbox" / "*.md"):
                raise RuntimeError(f"{_r0} did not receive dispatch")

            write(
                root / "dispatch" / _r0 / "reports" / f"{_r0}.md",
                f"FROM: {_r0}\nTO: {_coder}\nTYPE: review_response\nTASK_ID: SMOKE-1\nVERDICT: approved\n---\nApproved.\n"
            )

            if not wait_for(root / "dispatch" / _coder / "inbox" / "*merged*.md"):
                raise RuntimeError(f"{_coder} did not receive merged feedback")

            print("SMOKE TEST PASS")
            return 0
        finally:
            write(root / ".orchestrator" / "runtime_flags" / "STOP", "stop\n")
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
