#!/usr/bin/env python3
"""Test C3: install_hooks wires dispatch_gate for all agents; monitor_ingest only for executors."""
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
SCRIPT = ROOT / "scripts/install_hooks.py"

_CONFIG = {
    "project": "c3-test",
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
        "logs": ".orchestrator/logs",
    },
    "agents": [
        {"name": "gate-ralph", "executor": True},
        {"name": "gate-architect", "executor": False},
    ],
    "gate": {"protected_branches": ["dev", "main"], "consensus_rule": "unanimous",
             "require_approvals_from": ["gate-architect"], "max_rework_rounds": 3},
    "routing": {"cc_all": [], "escalation_target": "allan"},
    "fan_in": {}, "wake": {}, "session": {},
}

def run_for_agent(tmp: Path, agent: str) -> dict:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--agent", agent, "--project", str(tmp)],
        capture_output=True, text=True, cwd=str(tmp),
    )
    assert r.returncode == 0, f"install_hooks failed for {agent}: {r.stderr}"
    return json.loads(r.stdout)

def hook_cmds(hooks_dict: dict, event: str) -> list:
    return [
        h.get("command", "")
        for entry in hooks_dict.get("hooks", {}).get(event, [])
        for h in entry.get("hooks", [])
    ]

def check(label, condition, detail=""):
    ok = bool(condition)
    print(f"{'PASS' if ok else 'FAIL'}: {label}" + (f" ({detail})" if detail else ""))
    return ok

def check_gate_outer_if(hooks_dict: dict) -> list:
    """Return PreToolUse entries that contain check_gate in their hooks."""
    return [
        entry for entry in hooks_dict.get("hooks", {}).get("PreToolUse", [])
        if any("check_gate" in h.get("command", "") for h in entry.get("hooks", []))
    ]

if __name__ == "__main__":
    passed = True
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
        (tmp / ".orchestrator/config.json").write_text(json.dumps(_CONFIG), encoding="utf-8")

        # ralph (executor): must have dispatch_gate + inbox_access_guard + check_gate + monitor_ingest
        ralph = run_for_agent(tmp, "gate-ralph")
        pre = hook_cmds(ralph, "PreToolUse")
        post = hook_cmds(ralph, "PostToolUse")
        passed &= check("ralph: dispatch_gate in PreToolUse",
                        any("dispatch_gate" in c for c in pre), str(pre))
        passed &= check("ralph: inbox_access_guard in PreToolUse",
                        any("inbox_access_guard" in c for c in pre), str(pre))
        passed &= check("ralph: check_gate in PreToolUse",
                        any("check_gate" in c for c in pre), str(pre))
        cg_entries = check_gate_outer_if(ralph)
        passed &= check("ralph: check_gate if-condition on outer entry",
                        all(e.get("if") == "Bash(git commit *)" for e in cg_entries),
                        str(cg_entries))
        passed &= check("ralph: check_gate if NOT on inner hook",
                        all("if" not in h for e in cg_entries for h in e.get("hooks", [])),
                        str(cg_entries))
        passed &= check("ralph: monitor_ingest in PostToolUse",
                        any("monitor_ingest" in c for c in post), str(post))

        # gate-architect (non-executor): dispatch_gate + inbox_access_guard; NO check_gate or monitor_ingest
        arch = run_for_agent(tmp, "gate-architect")
        arch_pre = hook_cmds(arch, "PreToolUse")
        arch_post = hook_cmds(arch, "PostToolUse")
        passed &= check("gate-architect: dispatch_gate in PreToolUse",
                        any("dispatch_gate" in c for c in arch_pre), str(arch_pre))
        passed &= check("gate-architect: inbox_access_guard in PreToolUse",
                        any("inbox_access_guard" in c for c in arch_pre), str(arch_pre))
        passed &= check("gate-architect: NO check_gate",
                        not any("check_gate" in c for c in arch_pre), str(arch_pre))
        passed &= check("gate-architect: NO monitor_ingest",
                        not any("monitor_ingest" in c for c in arch_post), str(arch_post))

        # --all: both agents appear in output, exit 0
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--all", "--project", str(tmp)],
            capture_output=True, text=True, cwd=str(tmp),
        )
        passed &= check("--all exits 0", r.returncode == 0,
                        f"exit={r.returncode}\n{r.stderr[:200]}")
        passed &= check("--all output mentions ralph", "gate-ralph" in r.stdout)
        passed &= check("--all output mentions gate-architect", "gate-architect" in r.stdout)

        # existing hooks preserved after merge
        sf = tmp / "test_settings.json"
        sf.write_text(json.dumps({"hooks": {"PreToolUse": [
            {"matcher": "Read", "hooks": [{"type": "command", "command": "existing-hook"}]}
        ]}}), encoding="utf-8")
        subprocess.run(
            [sys.executable, str(SCRIPT), "--agent", "gate-ralph",
             "--project", str(tmp), "--settings-file", str(sf)],
            capture_output=True, text=True, cwd=str(tmp),
        )
        merged_pre = hook_cmds(json.loads(sf.read_text()), "PreToolUse")
        passed &= check("existing hook preserved after merge",
                        any("existing-hook" in c for c in merged_pre), str(merged_pre))

    sys.exit(0 if passed else 1)
