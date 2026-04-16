from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.common import active_reviewers, agent_names, clear_halt, current_task_id, is_halted, load_project_config, read_json, resolve_path, resolve_project_root, timestamp, write_json  # noqa: E402


@dataclass
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    exit_code: int


def _run(command: list[str], cwd: Path | None = None) -> CommandResult:
    proc = subprocess.run(command, capture_output=True, text=True, cwd=str(cwd) if cwd else None)
    return CommandResult(proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)


class DispatcherBackend:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = resolve_project_root(project_root) if project_root else ROOT
        self.engine_root = ROOT
        self.python = sys.executable
        self.orchctl = self.engine_root / "scripts" / "orchestratorctl.py"
        self.psmux = shutil.which("psmux") or "psmux"
        self.reload()

    def reload(self) -> None:
        self.config = load_project_config(self.project_root)
        self.dispatch_root = resolve_path("dispatch_root", self.project_root, self.config)
        self.tasks_dir = resolve_path("tasks", self.project_root, self.config)
        self.current_task_file = resolve_path("current_task", self.project_root, self.config)
        self.runtime_flags = resolve_path("runtime_flags", self.project_root, self.config)
        self.logs_dir = resolve_path("logs", self.project_root, self.config)
        self.audit_log = resolve_path("audit_log", self.project_root, self.config)
        self.decision_trace = resolve_path("decision_trace", self.project_root, self.config)
        self.merged_verdicts = resolve_path("merged_verdicts", self.project_root, self.config)
        self.trackers = resolve_path("trackers", self.project_root, self.config)
        self.halts = resolve_path("halts", self.project_root, self.config)
        self.sprint_profiles = self.project_root / ".orchestrator" / "sprint_profiles"
        self.roles_json = Path.home() / ".claude" / "hooks" / "roles.json"
        self.settings_local = self.project_root / ".claude" / "settings.local.json"

    def set_project_root(self, project_root: str | Path) -> None:
        self.project_root = resolve_project_root(project_root)
        self.reload()

    def run_orchctl(self, *args: str) -> CommandResult:
        return _run([self.python, str(self.orchctl), *args], cwd=self.project_root)

    def _session_name(self, agent_name: str) -> str:
        prefix = ((self.config.get("session") or {}).get("session_prefix") or "").strip()
        if prefix and agent_name.startswith(prefix):
            return agent_name
        return f"{prefix}{agent_name}" if prefix else agent_name

    def list_tasks(self) -> list[dict]:
        data = read_json(self.tasks_dir / "tasks.json", [])
        return data if isinstance(data, list) else []

    def current_task(self) -> dict:
        data = read_json(self.current_task_file, {})
        return data if isinstance(data, dict) else {}

    def _load_trackers(self) -> dict:
        data = read_json(self.trackers, {})
        return data if isinstance(data, dict) else {}

    def _load_verdict(self, task_id: str) -> dict:
        data = read_json(self.merged_verdicts / f"{task_id}.json", {})
        return data if isinstance(data, dict) else {}

    def _watcher_text(self) -> str:
        pid_file = self.runtime_flags / "watcher.pid"
        if not pid_file.exists():
            return "Not running"
        return f"PID {pid_file.read_text(encoding='utf-8').strip()}"

    def status_snapshot(self) -> dict:
        self.reload()
        current = self.current_task()
        task_id = current_task_id(current)
        gate = "No verdicts"
        if task_id:
            trackers = self._load_trackers()
            if task_id in trackers:
                tracker = trackers[task_id]
                required = tracker.get("required", []) or []
                received = list((tracker.get("received") or {}).keys())
                missing = [name for name in required if name not in received]
                gate = f"Waiting on {', '.join(missing)}" if missing else "Fan-in complete"
            else:
                verdict = self._load_verdict(task_id)
                if verdict:
                    gate = verdict.get("verdict", "unknown")
        agents = []
        for agent in agent_names(self.config):
            halted, reason = is_halted(agent, self.project_root, self.config)
            inbox = self.dispatch_root / agent / "inbox"
            agents.append(
                {
                    "name": agent,
                    "ready": (self.dispatch_root / agent / "ready").exists(),
                    "halted": halted,
                    "halt_reason": reason,
                    "session": self._session_name(agent),
                    "inbox_count": len(list(inbox.glob("*"))) if inbox.exists() else 0,
                }
            )
        return {
            "project": self.config.get("project", "unknown"),
            "project_root": str(self.project_root),
            "watcher": self._watcher_text(),
            "current_task": task_id,
            "current_title": current.get("title", "") if current else "",
            "gate": gate,
            "reviewers": active_reviewers(self.config),
            "agents": agents,
            "logs_dir": str(self.logs_dir),
            "audit_log": str(self.audit_log),
            "decision_trace": str(self.decision_trace),
        }

    def start_watcher(self) -> CommandResult:
        script = self.engine_root / "scripts" / "watcher.py"
        self.runtime_flags.mkdir(parents=True, exist_ok=True)
        stop_file = self.runtime_flags / "STOP"
        if stop_file.exists():
            stop_file.unlink()
        proc = subprocess.Popen(
            [self.python, str(script), str(self.project_root)],
            cwd=str(self.project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        (self.runtime_flags / "watcher.pid").write_text(str(proc.pid), encoding="utf-8")
        return CommandResult(True, f"watcher started pid={proc.pid}", "", 0)

    def kill_watcher(self) -> CommandResult:
        self.runtime_flags.mkdir(parents=True, exist_ok=True)
        (self.runtime_flags / "STOP").write_text("force-kill", encoding="utf-8")
        pid_file = self.runtime_flags / "watcher.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
                _run(["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"])
            except Exception:
                pass
            pid_file.unlink(missing_ok=True)
        return CommandResult(True, "watcher kill requested", "", 0)

    def reset_watcher_state(self) -> CommandResult:
        if self.trackers.exists():
            self.trackers.unlink()
        if self.merged_verdicts.exists():
            for item in self.merged_verdicts.glob("*.json"):
                item.unlink()
        self.kill_watcher()
        return self.start_watcher()

    def pause_sprint(self) -> CommandResult:
        self.halts.mkdir(parents=True, exist_ok=True)
        for agent_cfg in self.config.get("agents", []):
            if agent_cfg.get("executor"):
                (self.halts / f"{agent_cfg['name']}.flag").write_text("sprint paused", encoding="utf-8")
        return CommandResult(True, "sprint paused", "", 0)

    def resume_sprint(self) -> CommandResult:
        for agent_cfg in self.config.get("agents", []):
            if agent_cfg.get("executor"):
                clear_halt(agent_cfg["name"], self.project_root, self.config)
        return CommandResult(True, "sprint resumed", "", 0)

    def stop_sprint(self) -> CommandResult:
        self.runtime_flags.mkdir(parents=True, exist_ok=True)
        (self.runtime_flags / "STOP").write_text("stopped by desktop", encoding="utf-8")
        return CommandResult(True, "sprint stop requested", "", 0)

    def _session_exists(self, session_name: str) -> bool:
        return _run([self.psmux, "has-session", "-t", session_name]).ok

    def launch_agent(self, agent_name: str, mode: str, model: str = "", command: str = "") -> CommandResult:
        session = self._session_name(agent_name)
        if self._session_exists(session):
            return CommandResult(True, f"session already exists: {session}", "", 0)
        _run([self.psmux, "new-session", "-d", "-s", session, "-c", str(self.project_root)])
        _run([self.psmux, "send-keys", "-t", session, f"$env:GATE_AGENT_NAME = '{agent_name}'", "Enter"])
        if mode == "claude":
            _run([self.psmux, "send-keys", "-t", session, "claude", "Enter"])
        elif mode == "claude_resume":
            _run([self.psmux, "send-keys", "-t", session, "claude --resume", "Enter"])
        elif mode == "claude_model":
            _run([self.psmux, "send-keys", "-t", session, f"claude --model {model or 'opus'}", "Enter"])
        elif mode == "custom" and command:
            _run([self.psmux, "send-keys", "-t", session, command, "Enter"])
        return CommandResult(True, f"launched {agent_name} in {session}", "", 0)

    def attach_agent(self, agent_name: str) -> CommandResult:
        session = self._session_name(agent_name)
        if not self._session_exists(session):
            return CommandResult(False, "", f"no session for {agent_name}", 1)
        subprocess.Popen(["pwsh", "-NoExit", "-Command", f"psmux a -t '{session}'"])
        return CommandResult(True, f"attached to {session}", "", 0)

    def list_hook_states(self) -> list[dict]:
        flag_dir = self.runtime_flags / "hooks"
        flag_dir.mkdir(parents=True, exist_ok=True)
        hooks = ["dispatch_gate", "inbox_access_guard", "check_gate", "activity_logger", "monitor_ingest", "dispatch_next_bug", "on_file_message", "stop_notify"]
        return [{"name": hook, "enabled": not (flag_dir / f"{hook}.disabled").exists()} for hook in hooks]

    def toggle_hook(self, hook_name: str, enable: bool | None = None) -> CommandResult:
        flag_dir = self.runtime_flags / "hooks"
        flag_dir.mkdir(parents=True, exist_ok=True)
        flag = flag_dir / f"{hook_name}.disabled"
        current = not flag.exists()
        enable = (not current) if enable is None else enable
        if enable:
            flag.unlink(missing_ok=True)
        else:
            flag.write_text("disabled by desktop", encoding="utf-8")
        return CommandResult(True, f"{hook_name}={'enabled' if enable else 'disabled'}", "", 0)

    def set_all_hooks(self, enable: bool) -> CommandResult:
        for hook in self.list_hook_states():
            self.toggle_hook(hook["name"], enable)
        return CommandResult(True, "all hooks updated", "", 0)

    def reviewer_matrix(self) -> dict:
        reviewers = self.config.get("reviewers") or {}
        return {
            "available": reviewers.get("available") or [],
            "active": reviewers.get("active") or [],
            "presets": reviewers.get("presets") or {},
        }

    def apply_reviewer_preset(self, preset: str) -> CommandResult:
        return self.run_orchctl("reviewers", "preset", preset, str(self.project_root))

    def set_reviewer_enabled(self, reviewer: str, enable: bool) -> CommandResult:
        sub = "enable" if enable else "disable"
        return self.run_orchctl("reviewers", sub, reviewer, str(self.project_root))

    def list_task_choices(self) -> list[dict]:
        return [{"task_id": current_task_id(task), "title": task.get("title", ""), "status": task.get("status", "")} for task in self.list_tasks()]

    def dispatch_task_to_executor(self, task_id: str, reason: str = "dispatch") -> CommandResult:
        tasks = self.list_tasks()
        task = next((item for item in tasks if current_task_id(item) == task_id), None)
        if not task:
            return CommandResult(False, "", f"task not found: {task_id}", 1)
        for item in tasks:
            if current_task_id(item) == task_id:
                item["status"] = "in_progress"
        write_json(self.tasks_dir / "tasks.json", tasks)
        write_json(self.current_task_file, task)
        executors = [agent["name"] for agent in self.config.get("agents", []) if agent.get("executor")]
        if not executors:
            return CommandResult(False, "", "no executor configured", 1)
        target = executors[0]
        inbox = self.dispatch_root / target / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        lines = [
            "FROM: dispatcher",
            f"TO: {target}",
            "TYPE: task",
            f"TASK_ID: {task_id}",
            "---",
            f"Task ID: {task_id}",
            f"Title: {task.get('title', '')}",
            "",
            "Acceptance Criteria:",
        ]
        for item in task.get("acceptance_criteria", []):
            lines.append(f"- {item}")
        if task.get("reference_paths"):
            lines.extend(["", "Reference Paths:"])
            for item in task["reference_paths"]:
                lines.append(f"- {item}")
        (inbox / f"{reason}_{task_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return CommandResult(True, f"task {task_id} dispatched to {target}", "", 0)

    def override_verdict(self, task_id: str, verdict: str, reason: str = "") -> CommandResult:
        args = ["override", str(self.project_root), "--task", task_id, "--verdict", verdict]
        if reason:
            args.extend(["--reason", reason])
        return self.run_orchctl(*args)

    def send_direct_message(self, recipient: str, message: str, task_id: str = "") -> CommandResult:
        args = ["send", str(self.project_root), recipient, message, "--type", "direct_message"]
        if task_id:
            args.extend(["--task-id", task_id])
        return self.run_orchctl(*args)

    def clear_halt_flags(self) -> CommandResult:
        outputs = []
        for agent_name in agent_names(self.config):
            outputs.append(self.run_orchctl("resume", str(self.project_root), "--agent", agent_name))
        ok = all(item.ok for item in outputs)
        stdout = "\n".join(item.stdout.strip() for item in outputs if item.stdout.strip())
        stderr = "\n".join(item.stderr.strip() for item in outputs if item.stderr.strip())
        return CommandResult(ok, stdout, stderr, 0 if ok else 1)

    def set_sprint_mode(self, on: bool) -> CommandResult:
        profile_name = "sprint_on.json" if on else "sprint_off.json"
        profile_path = self.sprint_profiles / profile_name
        if not profile_path.exists():
            return CommandResult(False, "", f"missing profile {profile_name}", 1)
        if not self.roles_json.exists():
            return CommandResult(False, "", f"missing roles.json: {self.roles_json}", 1)
        roles = json.loads(self.roles_json.read_text(encoding="utf-8"))
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        roles.setdefault("roles", {})
        for key, value in (profile.get("roles") or {}).items():
            roles["roles"][key] = value
        roles.setdefault("hooks_config", {})
        for key, value in (profile.get("hooks_config") or {}).items():
            roles["hooks_config"][key] = value
        self.roles_json.write_text(json.dumps(roles, indent=2), encoding="utf-8")
        return CommandResult(True, f"sprint mode {'on' if on else 'off'}", "", 0)

    def folder_override_state(self) -> dict:
        if not self.roles_json.exists():
            return {"enabled": False, "paths": []}
        roles = json.loads(self.roles_json.read_text(encoding="utf-8"))
        folder_overrides = ((roles.get("hooks_config") or {}).get("folder_overrides") or {})
        return {"enabled": bool(folder_overrides.get("enabled", False)), "paths": folder_overrides.get("paths") or []}

    def set_folder_override(self, enabled: bool | None = None, paths: list[str] | None = None) -> CommandResult:
        if not self.roles_json.exists():
            return CommandResult(False, "", f"missing roles.json: {self.roles_json}", 1)
        roles = json.loads(self.roles_json.read_text(encoding="utf-8"))
        hook_config = roles.setdefault("hooks_config", {})
        folder_overrides = hook_config.setdefault("folder_overrides", {"enabled": False, "paths": [".claude/", "secrets/"]})
        if enabled is not None:
            folder_overrides["enabled"] = enabled
        if paths is not None:
            folder_overrides["paths"] = paths
        self.roles_json.write_text(json.dumps(roles, indent=2), encoding="utf-8")
        return CommandResult(True, "folder overrides updated", "", 0)

    def backup_settings(self) -> CommandResult:
        created = []
        for target in (self.roles_json, self.settings_local):
            if target.exists():
                backup_dir = target.parent / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = timestamp(self.config).replace(":", "-").replace(" ", "_")
                backup = backup_dir / f"{target.name}.bak.{stamp}"
                shutil.copy2(target, backup)
                created.append(str(backup))
        return CommandResult(True, "\n".join(created), "", 0)

    def deploy_to_project(self, target_root: str | Path) -> CommandResult:
        target = Path(target_root)
        orch_target = target / ".orchestrator"
        dispatch_target = target / "dispatch"
        orch_target.mkdir(parents=True, exist_ok=True)

        config_target = orch_target / "config.json"
        seed_path = self.engine_root / "artifacts" / "install" / "config" / "config.seed.json"
        if not config_target.exists():
            if seed_path.exists():
                seed = json.loads(seed_path.read_text(encoding="utf-8"))
                seed["project"] = target.name
                config_target.write_text(json.dumps(seed, indent=2), encoding="utf-8")
            else:
                config_target.write_text(json.dumps({"project": target.name, "agents": []}, indent=2), encoding="utf-8")

        config = json.loads(config_target.read_text(encoding="utf-8"))
        for key in ("plans", "tasks", "diffs", "merged_verdicts", "halts", "runtime_flags", "logs"):
            (target / config["paths"][key]).mkdir(parents=True, exist_ok=True)

        agents = [item["name"] for item in config.get("agents", []) if item.get("name")]
        if not agents:
            agents = agent_names(self.config)
        for agent in agents:
            for subdir in ("inbox", "outbox", "reports", "done", "archive"):
                (dispatch_target / agent / subdir).mkdir(parents=True, exist_ok=True)

        sprint_profile_dir = orch_target / "sprint_profiles"
        sprint_profile_dir.mkdir(parents=True, exist_ok=True)
        for profile_name in ("sprint_on.json", "sprint_off.json"):
            profile_path = sprint_profile_dir / profile_name
            if not profile_path.exists():
                profile_path.write_text(
                    json.dumps(
                        {
                            "roles": {},
                            "hooks_config": {
                                "sprint_active": profile_name == "sprint_on.json",
                                "auto_approve_mode": "sprint" if profile_name == "sprint_on.json" else "disabled",
                            },
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

        engine_root = None
        shared = self.config.get("shared_roots") or {}
        for key in ("orchestrator_primary", "orchestrator_fallback"):
            candidate = shared.get(key)
            if candidate and Path(candidate).exists():
                engine_root = Path(candidate)
                break
        if engine_root:
            install_script = engine_root / "scripts" / "install_hooks.py"
            if install_script.exists():
                result = _run([self.python, str(install_script), "--all", "--project", str(target)], cwd=engine_root)
                if not result.ok:
                    return result
        return CommandResult(True, f"deployed to project {target}", "", 0)

    def deploy_engine(self, target_root: str | Path) -> CommandResult:
        target = Path(target_root)
        target.mkdir(parents=True, exist_ok=True)
        copy_dirs = [
            "hooks",
            "lib",
            "scripts",
            "schemas",
            "bin",
            "tests",
            "mcp-server",
            "agents/profiles",
            "agents/protocols",
        ]
        copy_files = ["VERSION", "SETUP.md", "QUICKSTART.md", "COMMANDS.md", "SMOKE_TEST.md"]
        for directory in copy_dirs:
            src = self.engine_root / Path(directory)
            dst = target / Path(directory)
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)
        for file_name in copy_files:
            src = self.engine_root / file_name
            if src.exists():
                (target / file_name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target / file_name)
        return CommandResult(True, f"engine deployed to {target}", "", 0)

    def list_backups(self) -> list[dict]:
        backups = []
        for target in (self.roles_json, self.settings_local):
            backup_dir = target.parent / "backups"
            if backup_dir.exists():
                for item in sorted(backup_dir.glob(f"{target.name}.bak.*"), reverse=True):
                    backups.append({"label": item.name, "path": str(item), "target": str(target)})
        return backups

    def restore_backup(self, backup_path: str, target_path: str) -> CommandResult:
        backup = Path(backup_path)
        target = Path(target_path)
        if not backup.exists():
            return CommandResult(False, "", f"missing backup: {backup}", 1)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
        return CommandResult(True, f"restored {backup.name}", "", 0)

    def open_path(self, path: str) -> CommandResult:
        target = Path(path)
        if not target.exists():
            return CommandResult(False, "", f"path not found: {path}", 1)
        os.startfile(str(target))
        return CommandResult(True, f"opened {path}", "", 0)
