#!/usr/bin/env python3
"""Test E1: check_gate.py — reads merged_verdicts, checks protected_branches."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
HOOK = ROOT / "hooks/check_gate.py"

_CONFIG = {
    "project": "e1-test",
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
        "runtime_flags": ".orchestrator/runtime_flags", "logs": ".orchestrator/logs",
    },
    "agents": [{"name": "gate-ralph", "executor": True}],
    "gate": {"protected_branches": ["dev", "main"], "consensus_rule": "unanimous",
             "require_approvals_from": ["gate-architect"], "max_rework_rounds": 3},
    "routing": {"cc_all": [], "escalation_target": "allan"},
    "fan_in": {}, "wake": {}, "session": {"session_prefix": "gate-"},
}

def setup(tmp: Path, task_id="T42", verdict=None):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator/config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    (tmp / ".orchestrator/current_task.json").write_text(
        json.dumps({"id": task_id}), encoding="utf-8"
    )
    if verdict is not None:
        vdir = tmp / ".orchestrator/merged_verdicts"
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / f"{task_id}.json").write_text(json.dumps(verdict), encoding="utf-8")

def run_commit(tmp: Path, command="git commit -m 'x'", agent="gate-ralph"):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True,
        env={**os.environ, "GATE_AGENT_NAME": agent},
        cwd=str(tmp),
    )

def check(label, result, expect_exit):
    ok = result.returncode == expect_exit
    print(f"{'PASS' if ok else 'FAIL'}: {label} (exit={result.returncode}, want={expect_exit})")
    if not ok:
        print(f"  stdout: {result.stdout[:300]}")
        print(f"  stderr: {result.stderr[:200]}")
    return ok

if __name__ == "__main__":
    passed = True
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # P3: no agent name -> allow (exit 0)
        setup(tmp)
        r = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}),
            capture_output=True, text=True, cwd=str(tmp),
            env={k: v for k, v in os.environ.items() if k != "GATE_AGENT_NAME"},
        )
        passed &= check("P3: no agent -> allow", r, 0)

        # non-commit tool -> allow (exit 0)
        setup(tmp)
        r = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.py", "content": ""}}),
            capture_output=True, text=True, cwd=str(tmp),
            env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
        )
        passed &= check("Write tool -> allow", r, 0)

        # no merged verdict -> blocked (exit 2)
        setup(tmp)
        passed &= check("no verdict -> blocked", run_commit(tmp), 2)

        # approved verdict -> allow (exit 0)
        setup(tmp, verdict={"task_id": "T42", "verdict": "approved"})
        passed &= check("approved verdict -> allow", run_commit(tmp), 0)

        # rejected verdict -> blocked (exit 2)
        setup(tmp, verdict={"task_id": "T42", "verdict": "rejected", "reason": "critic said no",
                            "dissent": ["gate-architect"]})
        passed &= check("rejected verdict -> blocked", run_commit(tmp), 2)

        # no task_id in current_task -> blocked (exit 2)
        setup(tmp)
        (tmp / ".orchestrator/current_task.json").write_text(json.dumps({}), encoding="utf-8")
        passed &= check("no task_id -> blocked", run_commit(tmp), 2)

        # malformed stdin -> allow (exit 0) — hook should not crash
        setup(tmp)
        r = subprocess.run(
            [sys.executable, str(HOOK)],
            input="NOT VALID JSON",
            capture_output=True, text=True,
            env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
            cwd=str(tmp),
        )
        passed &= check("malformed stdin -> allow", r, 0)

        # non-protected branch -> allow freely even with no verdict
        setup(tmp)
        import subprocess as _sp
        _sp.run(["git", "init"], cwd=str(tmp), capture_output=True)
        # Make an initial commit so git rev-parse returns the actual branch name
        _env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test",
                "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test"}
        _sp.run(["git", "commit", "--allow-empty", "-m", "init"],
                cwd=str(tmp), capture_output=True, env=_env)
        _sp.run(["git", "checkout", "-b", "feature/my-work"],
                cwd=str(tmp), capture_output=True)
        passed &= check("non-protected branch -> allow", run_commit(tmp), 0)

    sys.exit(0 if passed else 1)
