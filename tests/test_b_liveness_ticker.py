#!/usr/bin/env python3
"""Test B: liveness ticker logic (unit test, no thread)."""
import json, os, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_CONFIG = {
    "project": "liveness-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents"
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "current_task": ".orchestrator/current_task.json",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "audit_log": ".orchestrator/audit.log",
        "decision_trace": ".orchestrator/decision_trace.log",
        "trackers": ".orchestrator/trackers.json",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True},
        {"name": "gate-architect", "executor": False},
    ],
    "gate": {},
    "routing": {"cc_all": [], "escalation_target": "allan"},
    "fan_in": {},
    "wake": {
        "mechanism": "tmux",
        "liveness_check_interval_seconds": 1,
        "idle_threshold_seconds": 2,
        "retry_interval_seconds": 10,
        "first_attempt_seconds": 0,
        "max_retries": 2,
        "monitor_pulse_seconds": 60,
    },
    "session": {"require_ready_files": False, "session_prefix": "gate-", "timezone": "UTC"},
}


def setup(tmp: Path):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    (tmp / ".orchestrator" / "logs").mkdir(parents=True, exist_ok=True)
    for agent in ["gate-ralph", "gate-architect"]:
        for sub in ["inbox", "outbox", "reports", "done", "archive"]:
            (tmp / "dispatch" / agent / sub).mkdir(parents=True, exist_ok=True)


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


if __name__ == "__main__":
    # Import the liveness check function directly
    from scripts.watcher import liveness_check_once

    passed = True
    _orig_cwd = os.getcwd()

    td_obj = tempfile.TemporaryDirectory()
    td = td_obj.name
    try:
        tmp = Path(td)
        setup(tmp)
        os.chdir(str(tmp))

        dispatch_root = tmp / "dispatch"
        ltu_dir = tmp / ".orchestrator" / "last_tool_use"
        ltu_dir.mkdir(parents=True, exist_ok=True)
        wake_cooldowns = {}

        # Case 1: no last_tool_use file -> skip (no wake)
        agents_to_wake = liveness_check_once(
            agent_names=["gate-ralph", "gate-architect"],
            dispatch_root=dispatch_root,
            ltu_dir=ltu_dir,
            idle_threshold_seconds=2,
            retry_interval_seconds=10,
            wake_cooldowns=wake_cooldowns,
            project_root=tmp,
            config=_CONFIG,
        )
        passed &= check("no ltu file -> no wake", len(agents_to_wake) == 0,
                        f"got {agents_to_wake}")

        # Case 2: ltu file exists but agent is active (recent timestamp)
        (ltu_dir / "ralph.ts").write_text(str(time.time()), encoding="utf-8")
        agents_to_wake = liveness_check_once(
            agent_names=["gate-ralph"],
            dispatch_root=dispatch_root,
            ltu_dir=ltu_dir,
            idle_threshold_seconds=2,
            retry_interval_seconds=10,
            wake_cooldowns=wake_cooldowns,
            project_root=tmp,
            config=_CONFIG,
        )
        passed &= check("active agent -> no wake", len(agents_to_wake) == 0,
                        f"got {agents_to_wake}")

        # Case 3: idle agent but empty inbox -> no wake
        (ltu_dir / "ralph.ts").write_text(str(time.time() - 100), encoding="utf-8")
        agents_to_wake = liveness_check_once(
            agent_names=["gate-ralph"],
            dispatch_root=dispatch_root,
            ltu_dir=ltu_dir,
            idle_threshold_seconds=2,
            retry_interval_seconds=10,
            wake_cooldowns=wake_cooldowns,
            project_root=tmp,
            config=_CONFIG,
        )
        passed &= check("idle + empty inbox -> no wake", len(agents_to_wake) == 0,
                        f"got {agents_to_wake}")

        # Case 4: idle agent with non-empty inbox -> wake
        (tmp / "dispatch" / "gate-ralph" / "inbox" / "msg.md").write_text("hello", encoding="utf-8")
        agents_to_wake = liveness_check_once(
            agent_names=["gate-ralph"],
            dispatch_root=dispatch_root,
            ltu_dir=ltu_dir,
            idle_threshold_seconds=2,
            retry_interval_seconds=10,
            wake_cooldowns=wake_cooldowns,
            project_root=tmp,
            config=_CONFIG,
        )
        passed &= check("idle + inbox -> wake", "gate-ralph" in agents_to_wake,
                        f"got {agents_to_wake}")

        # Case 5: cooldown prevents re-wake
        wake_cooldowns["gate-ralph"] = time.time()  # just woke
        agents_to_wake = liveness_check_once(
            agent_names=["gate-ralph"],
            dispatch_root=dispatch_root,
            ltu_dir=ltu_dir,
            idle_threshold_seconds=2,
            retry_interval_seconds=10,
            wake_cooldowns=wake_cooldowns,
            project_root=tmp,
            config=_CONFIG,
        )
        passed &= check("cooldown prevents re-wake", len(agents_to_wake) == 0,
                        f"got {agents_to_wake}")

        # Case 6: cooldown expired -> wake again
        wake_cooldowns["gate-ralph"] = time.time() - 20  # expired
        agents_to_wake = liveness_check_once(
            agent_names=["gate-ralph"],
            dispatch_root=dispatch_root,
            ltu_dir=ltu_dir,
            idle_threshold_seconds=2,
            retry_interval_seconds=10,
            wake_cooldowns=wake_cooldowns,
            project_root=tmp,
            config=_CONFIG,
        )
        passed &= check("cooldown expired -> wake", "gate-ralph" in agents_to_wake,
                        f"got {agents_to_wake}")

        # Case 7: .tmp files in inbox don't count
        # Remove the real message, add a .tmp
        (tmp / "dispatch" / "gate-ralph" / "inbox" / "msg.md").unlink()
        (tmp / "dispatch" / "gate-ralph" / "inbox" / "partial.tmp").write_text("x", encoding="utf-8")
        wake_cooldowns.clear()
        agents_to_wake = liveness_check_once(
            agent_names=["gate-ralph"],
            dispatch_root=dispatch_root,
            ltu_dir=ltu_dir,
            idle_threshold_seconds=2,
            retry_interval_seconds=10,
            wake_cooldowns=wake_cooldowns,
            project_root=tmp,
            config=_CONFIG,
        )
        passed &= check(".tmp files ignored -> no wake", len(agents_to_wake) == 0,
                        f"got {agents_to_wake}")

        # Case 8: trace entries written
        trace_path = tmp / ".orchestrator" / "decision_trace.log"
        if trace_path.exists():
            lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
            liveness_traces = [json.loads(l) for l in lines if "liveness" in l]
            passed &= check("liveness trace entries written", len(liveness_traces) > 0,
                            f"found {len(liveness_traces)}")
        else:
            passed &= check("trace file exists", False, "not created")

    finally:
        os.chdir(_orig_cwd)
        td_obj.cleanup()

    sys.exit(0 if passed else 1)
