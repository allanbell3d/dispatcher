#!/usr/bin/env python3
"""Test D6: dispatch_next_bug progresses tasks from canonical task_id state."""
import json
import os
import subprocess
import sys
import tempfile
from uuid import uuid4
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "dispatch_next_bug.py"
TMP_ROOT = Path(tempfile.gettempdir()) / "dispatcher-slice-tests"

_CONFIG = {
    "project": "d6-test",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents",
    },
    "paths": {
        "state_root": ".orchestrator",
        "dispatch_root": "dispatch",
        "tasks": ".orchestrator/tasks",
        "current_task": ".orchestrator/tasks/current_task.json",
        "merged_verdicts": ".orchestrator/merged_verdicts",
        "halts": ".orchestrator/halts",
        "audit_log": ".orchestrator/audit.log",
        "runtime_flags": ".orchestrator/runtime_flags",
        "logs": ".orchestrator/logs",
    },
    "session": {"halt_between_batches": True, "session_prefix": "gate-", "timezone": "UTC"},
    "routing": {},
    "fan_in": {},
    "wake": {},
    "gate": {},
    "agents": [{"name": "gate-ralph", "executor": True}],
}


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


def setup(tmp: Path):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")
    (tmp / ".orchestrator" / "tasks").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "merged_verdicts").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "runtime_flags").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "logs").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "tasks" / "current_task.json").write_text(
        json.dumps({"task_id": "T42", "batch": "B1"}), encoding="utf-8"
    )
    (tmp / ".orchestrator" / "tasks" / "tasks.json").write_text(
        json.dumps([
            {"task_id": "T42", "title": "Implement slice", "status": "in_progress", "batch": "B1"},
            {"task_id": "T43", "title": "Next slice", "status": "pending", "batch": "B2"},
        ]),
        encoding="utf-8",
    )
    (tmp / ".orchestrator" / "merged_verdicts" / "T42.json").write_text(
        json.dumps({"task_id": "T42", "verdict": "approved"}), encoding="utf-8"
    )


if __name__ == "__main__":
    passed = True
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    tmp = TMP_ROOT / f"task-progress-{uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=False)
    setup(tmp)

    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git commit -m 'fix: done [task:T42]'"},
            "tool_response": {},
            "exitCode": 0,
        }
    )
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "GATE_AGENT_NAME": "gate-ralph"},
        cwd=str(tmp),
    )

    passed &= check("hook exits 0", result.returncode == 0,
                    f"exit={result.returncode} stderr={result.stderr[:200]}")
    passed &= check("stdout omits legacy FILE/DETAILS fields",
                    "FILE:" not in result.stdout and "DETAILS:" not in result.stdout,
                    result.stdout[:500])

    current_task = json.loads((tmp / ".orchestrator" / "tasks" / "current_task.json").read_text(encoding="utf-8"))
    tasks = json.loads((tmp / ".orchestrator" / "tasks" / "tasks.json").read_text(encoding="utf-8"))
    passed &= check("current task advances by task_id", current_task.get("task_id") == "T43",
                    json.dumps(current_task))
    passed &= check("current task does not keep legacy id",
                    "id" not in current_task,
                    json.dumps(current_task))
    passed &= check("completed task marked done",
                    any(t.get("task_id") == "T42" and t.get("status") == "done" for t in tasks),
                    json.dumps(tasks))
    passed &= check("next task marked in_progress",
                    any(t.get("task_id") == "T43" and t.get("status") == "in_progress" for t in tasks),
                    json.dumps(tasks))
    archived = tmp / ".orchestrator" / "merged_verdicts" / "archive" / "T42.json"
    passed &= check("used merged verdict archived", archived.exists(), str(archived))

    sys.exit(0 if passed else 1)
