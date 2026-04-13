#!/usr/bin/env python3
"""Test D-T1: trace_hook() writes JSON-lines decision trace."""
import json, os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_CONFIG = {
    "project": "d1-test",
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
        {"name": "gate-monitor-1", "executor": False},
    ],
    "gate": {"protected_branches": ["dev", "main"], "consensus_rule": "unanimous",
             "require_approvals_from": ["gate-architect"], "max_rework_rounds": 3},
    "routing": {"cc_all": ["gate-monitor-1"], "escalation_target": "allan",
                "review_requests_to": ["gate-architect"]},
    "fan_in": {"review": {"required": ["gate-architect"], "timeout_seconds": 300,
                          "on_timeout": "escalate_allan"}},
    "wake": {"mechanism": "tmux", "first_attempt_seconds": 5, "retry_interval_seconds": 10,
             "max_retries": 2, "monitor_pulse_seconds": 60,
             "liveness_check_interval_seconds": 30, "idle_threshold_seconds": 120},
    "session": {"require_ready_files": False, "session_prefix": "gate-", "timezone": "UTC"},
}


def setup(tmp: Path):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(
        json.dumps(_CONFIG), encoding="utf-8"
    )


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


if __name__ == "__main__":
    from lib.common import resolve_project_root, load_project_config, trace_hook, resolve_path

    passed = True

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        setup(tmp)
        os.chdir(str(tmp))

        project_root = resolve_project_root(str(tmp))
        config = load_project_config(project_root)

        # T1: trace_hook writes a line
        trace_hook(
            hook="dispatch_gate",
            agent="gate-ralph",
            decision="allow",
            elapsed_ms=1.23,
            project_root=project_root,
            config=config,
            state="WORKING",
            tool="Write",
        )

        trace_path = resolve_path("logs", project_root, config) / "decision_trace.log"
        passed &= check("trace file created", trace_path.exists(), str(trace_path))

        if trace_path.exists():
            lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
            passed &= check("exactly one line", len(lines) == 1, f"got {len(lines)}")
            entry = json.loads(lines[0])
            passed &= check("has ts field", "ts" in entry)
            passed &= check("hook field", entry.get("hook") == "dispatch_gate")
            passed &= check("agent field", entry.get("agent") == "gate-ralph")
            passed &= check("decision field", entry.get("decision") == "allow")
            passed &= check("elapsed_ms field", abs(entry.get("elapsed_ms", 0) - 1.23) < 0.01)
            passed &= check("extra field state", entry.get("state") == "WORKING")
            passed &= check("extra field tool", entry.get("tool") == "Write")

        # T2: multiple writes append (O_APPEND)
        trace_hook(
            hook="check_gate",
            agent="gate-ralph",
            decision="deny",
            elapsed_ms=0.5,
            project_root=project_root,
            config=config,
            reason="no verdict",
        )
        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        passed &= check("two lines after second call", len(lines) == 2, f"got {len(lines)}")
        entry2 = json.loads(lines[1])
        passed &= check("second entry hook", entry2.get("hook") == "check_gate")
        passed &= check("second entry decision", entry2.get("decision") == "deny")

        # T3: trace_hook never raises (fail-silent like audit_log)
        try:
            trace_hook(
                hook="broken",
                agent="x",
                decision="x",
                elapsed_ms=0,
                project_root=Path("/nonexistent/path/that/will/fail"),
                config=None,
            )
            passed &= check("no exception on bad path", True)
        except Exception as e:
            passed &= check("no exception on bad path", False, str(e))

        # T4: trace_hook with no config uses defaults
        trace_hook(
            hook="activity_logger",
            agent="gate-ralph",
            decision="allow",
            elapsed_ms=2.0,
            project_root=project_root,
            config=None,
        )
        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        passed &= check("three lines after default-config call", len(lines) == 3, f"got {len(lines)}")

    sys.exit(0 if passed else 1)
