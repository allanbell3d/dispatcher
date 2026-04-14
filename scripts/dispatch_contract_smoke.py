#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import shutil
import subprocess
import time
import uuid

ARTIFACTS = ROOT / "artifacts"


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


def load_json(relative: str) -> dict | list:
    return json.loads((ARTIFACTS / relative).read_text(encoding="utf-8"))


def load_text(relative: str) -> str:
    return (ARTIFACTS / relative).read_text(encoding="utf-8")


def build_fixture(root: Path) -> None:
    """Build a minimal project fixture from the canonical artifact library."""
    cfg = load_json("install/config/config.seed.json")
    cfg["project"] = "smoke-test"
    cfg["shared_roots"] = {
        "orchestrator_primary": str(ROOT),
        "orchestrator_fallback": str(ROOT),
        "agents_primary": str(ROOT),
        "agents_fallback": str(ROOT),
    }
    cfg["wake"]["mechanism"] = "tmux"
    cfg["wake"]["first_attempt_seconds"] = 2
    cfg["wake"]["max_retries"] = 5
    cfg["wake"]["monitor_pulse_seconds"] = 10
    cfg["session"]["halt_between_batches"] = False
    cfg["agents"] = [
        {"name": "gate-ralph", "profile": "gate-ralph", "executor": True, "roles": ["coder"]},
        {"name": "gate-architect", "profile": "gate-architect", "executor": False, "roles": ["reviewer"]},
        {"name": "gate-monitor", "profile": "gate-monitor", "executor": False, "roles": ["monitor"]},
    ]
    cfg["reviewers"]["available"] = ["gate-architect"]
    cfg["reviewers"]["active"] = ["gate-architect"]
    cfg["reviewers"]["presets"] = {"classic": ["gate-architect"]}
    cfg["routing"]["review_requests_to"] = ["gate-architect"]
    cfg["routing"]["on_batch_complete"] = []
    cfg["routing"]["on_test_failure"] = ["gate-ralph"]
    cfg["routing"]["on_test_passed"] = ["gate-ralph"]
    cfg["routing"]["on_stop"] = ["gate-monitor"]
    cfg["gate"]["require_approvals_from"] = ["gate-architect"]
    cfg["fan_in"]["review"]["required"] = ["gate-architect"]
    cfg["fan_in"]["review"]["timeout_seconds"] = 1200

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
    scratch_root = ROOT.parents[1] if ROOT.parent.name == ".worktrees" else ROOT
    scratch = scratch_root / ".pytest_tmp_dispatch_contract_smoke" / f"run_{uuid.uuid4().hex}"
    root = scratch / "project"

    try:
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

            review = load_text("fixtures/dispatch/review_request.template.md").format(
                coder=_coder,
                reviewer=_r0,
                task_id="SMOKE-1",
            )
            write(root / "dispatch" / _coder / "outbox" / "review.md", review)

            if not wait_for(root / "dispatch" / _r0 / "inbox" / "*.md"):
                raise RuntimeError(f"{_r0} did not receive dispatch")

            write(
                root / "dispatch" / _r0 / "reports" / f"{_r0}.md",
                load_text("fixtures/dispatch/review_response.approved.template.md").format(
                    reviewer=_r0,
                    coder=_coder,
                    task_id="SMOKE-1",
                ),
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
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
