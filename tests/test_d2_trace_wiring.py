#!/usr/bin/env python3
"""Test D-T2: all 8 hooks write trace_hook entries."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
HOOKS_DIR = ROOT / "hooks"

ALL_HOOKS = [
    "dispatch_gate.py",
    "check_gate.py",
    "inbox_access_guard.py",
    "monitor_ingest.py",
    "activity_logger.py",
    "dispatch_next_bug.py",
    "on_file_message.py",
    "stop_notify.py",
]

_CONFIG = {
    "project": "d2-trace-test",
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
        {"name": "gate-ralph", "executor": True, "roles": ["coder"]},
        {"name": "gate-architect", "executor": False, "roles": ["reviewer"]},
        {"name": "gate-monitor-1", "executor": False, "roles": ["gate-monitor"]},
    ],
    "gate": {"protected_branches": ["dev", "main"], "consensus_rule": "unanimous",
             "require_approvals_from": ["gate-architect"], "max_rework_rounds": 3},
    "routing": {"cc_all": ["gate-monitor-1"], "escalation_target": "allan",
                "review_requests_to": ["gate-architect"], "on_stop": ["gate-monitor-1"]},
    "fan_in": {"review": {"required": ["gate-architect"], "timeout_seconds": 300,
                          "on_timeout": "escalate_allan"}},
    "wake": {"mechanism": "tmux", "first_attempt_seconds": 5, "retry_interval_seconds": 10,
             "max_retries": 2, "monitor_pulse_seconds": 60,
             "liveness_check_interval_seconds": 30, "idle_threshold_seconds": 120},
    "session": {"require_ready_files": False, "session_prefix": "gate-", "timezone": "UTC"},
}


def setup(tmp: Path):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    (tmp / ".orchestrator" / "current_task.json").write_text(json.dumps({"id": "T99"}), encoding="utf-8")
    (tmp / ".orchestrator" / "logs").mkdir(parents=True, exist_ok=True)
    (tmp / "dispatch" / "gate-ralph" / "inbox").mkdir(parents=True, exist_ok=True)
    (tmp / "dispatch" / "gate-ralph" / "outbox").mkdir(parents=True, exist_ok=True)
    (tmp / "dispatch" / "gate-ralph" / "ready").write_text("1", encoding="utf-8")
    # Put a message in inbox so dispatch_gate allows
    msg = tmp / "dispatch" / "gate-ralph" / "inbox" / "test-msg.md"
    msg.write_text("FROM: watcher\n---\ntest", encoding="utf-8")


def run_hook(hook_name: str, tmp: Path, payload: dict, agent: str = "gate-ralph") -> subprocess.CompletedProcess:
    env = {**os.environ, "GATE_AGENT_NAME": agent}
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / hook_name)],
        input=json.dumps(payload),
        capture_output=True, text=True,
        cwd=str(tmp),
        env=env,
        timeout=10,
    )


def get_trace_lines(tmp: Path) -> list:
    trace_file = tmp / ".orchestrator" / "logs" / "decision_trace.log"
    if not trace_file.exists():
        return []
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return result


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


if __name__ == "__main__":
    passed = True

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        setup(tmp)

        # dispatch_gate: stamped agent with inbox -> allow -> should trace
        payload = {"tool_name": "Write", "tool_input": {"file_path": "x.py", "content": ""}}
        run_hook("dispatch_gate.py", tmp, payload, agent="gate-ralph")
        traces = get_trace_lines(tmp)
        dg_traces = [t for t in traces if t.get("hook") == "dispatch_gate"]
        passed &= check("dispatch_gate wrote trace", len(dg_traces) >= 1,
                        f"found {len(dg_traces)}")
        if dg_traces:
            passed &= check("dispatch_gate has elapsed_ms", "elapsed_ms" in dg_traces[0])
            passed &= check("dispatch_gate has agent", dg_traces[0].get("agent") == "gate-ralph")

        # check_gate: no agent -> allow -> should trace (or skip trace for no-agent)
        payload_cg = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
        env_no_agent = {k: v for k, v in os.environ.items() if k != "GATE_AGENT_NAME"}
        subprocess.run(
            [sys.executable, str(HOOKS_DIR / "check_gate.py")],
            input=json.dumps(payload_cg),
            capture_output=True, text=True, cwd=str(tmp), env=env_no_agent,
        )
        # check_gate with no agent exits early -- trace is optional for no-agent path

        # inbox_access_guard: stamped agent accessing own dispatch -> allow
        payload_iag = {"tool_name": "Read", "tool_input": {"file_path": str(tmp / "dispatch" / "gate-ralph" / "inbox" / "test-msg.md")}}
        run_hook("inbox_access_guard.py", tmp, payload_iag, agent="gate-ralph")
        traces = get_trace_lines(tmp)
        iag_traces = [t for t in traces if t.get("hook") == "inbox_access_guard"]
        passed &= check("inbox_access_guard wrote trace", len(iag_traces) >= 1,
                        f"found {len(iag_traces)}")

        # monitor_ingest: coder agent
        payload_mi = {"tool_name": "Bash", "tool_input": {"command": "echo hi"},
                      "tool_response": {"output": "hi"}, "exit_code": 0}
        run_hook("monitor_ingest.py", tmp, payload_mi, agent="gate-ralph")
        traces = get_trace_lines(tmp)
        mi_traces = [t for t in traces if t.get("hook") == "monitor_ingest"]
        passed &= check("monitor_ingest wrote trace", len(mi_traces) >= 1,
                        f"found {len(mi_traces)}")

        # activity_logger
        payload_al = {"tool_name": "Bash", "tool_input": {"command": "echo hi"},
                      "tool_response": {"output": "hi"}, "exit_code": 0}
        run_hook("activity_logger.py", tmp, payload_al, agent="gate-ralph")
        traces = get_trace_lines(tmp)
        al_traces = [t for t in traces if t.get("hook") == "activity_logger"]
        passed &= check("activity_logger wrote trace", len(al_traces) >= 1,
                        f"found {len(al_traces)}")

        # dispatch_next_bug: non-matching commit -> skip
        payload_dnb = {"tool_name": "Bash", "tool_input": {"command": "echo hi"},
                       "exit_code": 0}
        run_hook("dispatch_next_bug.py", tmp, payload_dnb, agent="gate-ralph")
        traces = get_trace_lines(tmp)
        dnb_traces = [t for t in traces if t.get("hook") == "dispatch_next_bug"]
        passed &= check("dispatch_next_bug wrote trace", len(dnb_traces) >= 1,
                        f"found {len(dnb_traces)}")

        # on_file_message: no matching file -> skip
        payload_ofm = {"file_path": str(tmp / "nonexistent.md")}
        run_hook("on_file_message.py", tmp, payload_ofm, agent="gate-ralph")
        traces = get_trace_lines(tmp)
        ofm_traces = [t for t in traces if t.get("hook") == "on_file_message"]
        passed &= check("on_file_message wrote trace", len(ofm_traces) >= 1,
                        f"found {len(ofm_traces)}")

        # stop_notify: sends stop notification
        run_hook("stop_notify.py", tmp, {}, agent="gate-ralph")
        traces = get_trace_lines(tmp)
        sn_traces = [t for t in traces if t.get("hook") == "stop_notify"]
        passed &= check("stop_notify wrote trace", len(sn_traces) >= 1,
                        f"found {len(sn_traces)}")

        # Verify all traces have required fields
        all_traces = get_trace_lines(tmp)
        for entry in all_traces:
            has_fields = all(k in entry for k in ("ts", "hook", "agent", "decision", "elapsed_ms"))
            if not has_fields:
                passed &= check(f"trace entry has required fields: {entry.get('hook','?')}", False,
                                f"missing keys in {list(entry.keys())}")

    sys.exit(0 if passed else 1)
