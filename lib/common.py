#!/usr/bin/env python3
"""Dispatcher orchestrator — shared library."""
from __future__ import annotations

__version__ = "0.1.15"

import hashlib
import json
import os
import platform
import random
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# Legacy defaults removed — now read from config.shared_roots:
#   orchestrator_primary: W:/Claude_Library/orchestrator
#   orchestrator_fallback: D:/IA/orchestrator
#   agents_primary:        W:/Claude_Library/agents
#   agents_fallback:       D:/IA/agents
DEFAULT_TZ = "Asia/Dubai"
_FIXED_TZ_FALLBACKS = {
    "Asia/Dubai": timezone(timedelta(hours=4)),
}


def _resolve_tz(config: dict | None = None):
    tz_name = ((config or {}).get("session") or {}).get("timezone", DEFAULT_TZ)
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        return _FIXED_TZ_FALLBACKS.get(tz_name, timezone.utc)


def now_tz(config: dict | None = None) -> datetime:
    return datetime.now(_resolve_tz(config))


def timestamp(config: dict | None = None) -> str:
    return now_tz(config).strftime("%Y-%m-%d %H:%M:%S")


def file_stamp(config: dict | None = None) -> str:
    return now_tz(config).strftime("%Y%m%d-%H%M%S-%f")


def sanitize(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "message"


def atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def write_json(path: Path, data):
    atomic_write(path, json.dumps(data, indent=2) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def ensure_dispatch_dirs(dispatch_dir: Path, agent: str):
    for sub in ["inbox", "outbox", "reports", "done", "archive"]:
        (dispatch_dir / agent / sub).mkdir(parents=True, exist_ok=True)


def visible_dispatch_files(directory: Path) -> list[Path]:
    """Return real dispatch artifacts, excluding temp files and dotfile placeholders."""
    if not directory.is_dir():
        return []
    try:
        return [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix != ".tmp" and not path.name.startswith(".")
        ]
    except OSError:
        return []


def sort_files_by_mtime(paths):
    return sorted(paths, key=lambda p: (p.stat().st_mtime_ns, p.name))


def resolve_project_root(explicit: str | Path | None = None) -> Path:
    candidate = Path(explicit).resolve() if explicit else Path.cwd().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for probe in [candidate, *candidate.parents]:
        if (probe / ".orchestrator" / "config.json").exists():
            return probe
    raise FileNotFoundError("Could not resolve project root; expected .orchestrator/config.json")


def load_project_config(project_root: Path) -> dict:
    config_path = project_root / ".orchestrator" / "config.json"
    cfg = read_json(config_path, {})
    if not cfg:
        raise FileNotFoundError(f"Missing or invalid config: {config_path}")
    return cfg


def choose_existing(primary: Path, fallback: Path) -> Path:
    if primary.exists():
        return primary
    if fallback.exists():
        return fallback
    return primary


def resolve_shared_roots(config: dict) -> tuple[Path, Path]:
    env_orch = os.environ.get("ORCHESTRATOR_ROOT")
    env_agents = os.environ.get("AGENTS_ROOT")
    if env_orch and env_agents:
        return Path(env_orch), Path(env_agents)
    shared = config.get("shared_roots", {})
    orch = Path(env_orch) if env_orch else choose_existing(
        Path(shared.get("orchestrator_primary", r"W:/Claude_Library/orchestrator")),
        Path(shared.get("orchestrator_fallback", r"D:/IA/orchestrator")),
    )
    agents = Path(env_agents) if env_agents else choose_existing(
        Path(shared.get("agents_primary", r"W:/Claude_Library/agents")),
        Path(shared.get("agents_fallback", r"D:/IA/agents")),
    )
    return orch, agents



_PATH_KEY_DEFAULTS = {
    "state_root":      ".orchestrator",
    "dispatch_root":   "dispatch",
    "plans":           ".orchestrator/plans",
    "tasks":           ".orchestrator/tasks",
    "current_task":    ".orchestrator/tasks/current_task.json",
    "trackers":        ".orchestrator/trackers.json",
    "diffs":           ".orchestrator/diffs",
    "audit_log":       ".orchestrator/audit.log",
    "decision_trace":  ".orchestrator/logs/decision_trace.log",
    "merged_verdicts": ".orchestrator/merged_verdicts",
    "halts":           ".orchestrator/halts",
    "playwright_tests": "tests/e2e",
    "logs":             ".orchestrator/logs",
    "runtime_flags":    ".orchestrator/runtime_flags",
    "memory":           "memory",
    "docs":             "docs",
}


def resolve_path(key: str, project_root: Path, config: dict | None = None) -> Path:
    """
    Key-based path resolver for the round 1 config.paths contract.

    Source: MASTER_SPECS_MERGED.md section "Config shape".
    All path resolution uses this function. Adding a new logical path requires
    only a config entry or a new key in _PATH_KEY_DEFAULTS.

    Args:
        key: logical path name from config.paths (e.g. "audit_log", "diffs")
        project_root: project root Path (where .orchestrator/config.json lives)
        config: optional pre-loaded config; loaded from project_root if None

    Returns:
        pathlib.Path resolved against project_root (absolute).

    Raises:
        KeyError: key is not in config.paths AND not in _PATH_KEY_DEFAULTS.
    """
    if config is None:
        config = load_project_config(project_root)
    paths_cfg = config.get("paths", {}) or {}
    if key in paths_cfg:
        raw = paths_cfg[key]
    elif key in _PATH_KEY_DEFAULTS:
        raw = _PATH_KEY_DEFAULTS[key]
    else:
        raise KeyError(
            f"resolve_path: unknown path key '{key}'. "
            f"Not in config.paths and not in defaults "
            f"({sorted(_PATH_KEY_DEFAULTS.keys())})."
        )
    p = Path(raw)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def halt_flag_path(agent: str, project_root: Path, config: dict | None = None) -> Path:
    """Return the Path of the halt flag file for the given agent name."""
    halts_dir = resolve_path("halts", project_root, config)
    return halts_dir / f"{agent}.flag"


def is_halted(agent: str, project_root: Path, config: dict | None = None) -> tuple[bool, str]:
    """Check whether an agent halt flag is set.

    Returns:
        (True, reason) if the flag file exists; (False, "") otherwise.
    """
    flag = halt_flag_path(agent, project_root, config)
    if flag.exists():
        try:
            reason = flag.read_text(encoding="utf-8").strip()
        except OSError:
            reason = ""
        return True, reason
    return False, ""


def set_halt(agent: str, reason: str, project_root: Path, config: dict | None = None):
    """Write a halt flag for the given agent (atomic, P7-safe)."""
    flag = halt_flag_path(agent, project_root, config)
    atomic_write(flag, reason)


def clear_halt(agent: str, project_root: Path, config: dict | None = None):
    """Remove the halt flag for the given agent if it exists.

    Note: Halt flags are ephemeral runtime state, not logs or dispatch history.
    Rule #8 (nothing ever deleted) applies to audit logs, dispatch messages,
    and archived files — not to runtime control flags that are created and
    cleared within a single sprint lifecycle.
    """
    flag = halt_flag_path(agent, project_root, config)
    flag.unlink(missing_ok=True)


def is_hook_disabled(hook_name: str, project_root: Path = None, config: dict | None = None) -> bool:
    """Check if a hook is runtime-disabled via flag file.

    Flag file: <runtime_flags>/hooks/<hook_name>.disabled
    Returns True if the flag file exists (hook should exit immediately).
    Never raises -- returns False on any error (fail-open).
    """
    try:
        if project_root is None:
            project_root = resolve_project_root()
        flags_dir = resolve_path("runtime_flags", project_root, config)
        flag = flags_dir / "hooks" / f"{hook_name}.disabled"
        return flag.exists()
    except Exception:
        return False


def audit_log(event: str, project_root: Path = None, config: dict | None = None, **fields):
    """Append a JSON-lines audit entry (fail-open — never raises, P4 advisory).

    Each line written: {"ts": "<ISO8601>", "event": "<event>", ...fields}
    Uses O_APPEND for concurrent-safe writes without an exclusive lock.
    """
    try:
        if project_root is None:
            project_root = resolve_project_root()
        log_path = resolve_path("audit_log", project_root, config)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(_resolve_tz(config)).isoformat()
        entry = json.dumps({"ts": ts, "event": event, **fields}) + "\n"
        encoded = entry.encode("utf-8")
        fd = os.open(str(log_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, encoded)
        finally:
            os.close(fd)
    except Exception:
        pass


def trace_hook(
    hook: str,
    agent: str,
    decision: str,
    elapsed_ms: float,
    project_root: Path = None,
    config: dict | None = None,
    **fields,
):
    """Append a JSON-lines decision trace entry (fail-open -- never raises).

    Like audit_log() but dedicated to hook/watcher decision traces.
    Each line: {"ts": ..., "hook": ..., "agent": ..., "decision": ..., "elapsed_ms": ..., ...}
    Uses O_APPEND for concurrent-safe writes.
    """
    try:
        if project_root is None:
            project_root = resolve_project_root()

        # Command truncation — bound log size
        if "command" in fields:
            fields["command"] = str(fields["command"])[:200]

        # Session-ID filename variation
        session_id = ""
        try:
            flags_dir = resolve_path("runtime_flags", project_root, config)
            sid_file = Path(flags_dir) / "session_id"
            if sid_file.exists():
                session_id = sid_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        trace_path = resolve_path("decision_trace", project_root, config)
        if session_id:
            log_path = trace_path.with_name(f"{trace_path.stem}_{session_id}{trace_path.suffix}")
        else:
            log_path = trace_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(_resolve_tz(config)).isoformat()
        entry = json.dumps({
            "ts": ts,
            "hook": hook,
            "agent": agent,
            "decision": decision,
            "elapsed_ms": round(elapsed_ms, 3),
            **fields,
        }) + "\n"
        encoded = entry.encode("utf-8")
        fd = os.open(str(log_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, encoded)
        finally:
            os.close(fd)

        # Dual-write: NAS archive (fail-silent — NAS may be unreachable)
        try:
            shared = resolve_shared_roots(config or {})
            nas_root = shared[0]  # orchestrator_root
            if nas_root:
                nas_log_dir = Path(nas_root) / "logs" / (config or {}).get("project", "unknown")
                nas_log_dir.mkdir(parents=True, exist_ok=True)
                fd2 = os.open(str(nas_log_dir / log_path.name), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
                try:
                    os.write(fd2, encoded)
                finally:
                    os.close(fd2)
        except Exception:
            pass
    except Exception:
        pass


def agent_names(config: dict) -> list[str]:
    return [a.get("name") for a in config.get("agents", []) if a.get("name")]


def reviewers_available(config: dict) -> list[str]:
    reviewers_cfg = (config.get("reviewers") or {}).get("available")
    if isinstance(reviewers_cfg, list) and reviewers_cfg:
        return [str(name).strip() for name in reviewers_cfg if str(name).strip()]
    return [
        a.get("name")
        for a in config.get("agents", [])
        if a.get("name") and "reviewer" in (a.get("roles") or [])
    ]


def active_reviewers(config: dict) -> list[str]:
    reviewers_cfg = (config.get("reviewers") or {}).get("active")
    if isinstance(reviewers_cfg, list) and reviewers_cfg:
        return [str(name).strip() for name in reviewers_cfg if str(name).strip()]
    for legacy in (
        (config.get("routing") or {}).get("review_requests_to"),
        (config.get("gate") or {}).get("require_approvals_from"),
        ((config.get("fan_in") or {}).get("review") or {}).get("required"),
    ):
        if isinstance(legacy, list) and legacy:
            return [str(name).strip() for name in legacy if str(name).strip()]
    return reviewers_available(config)


def sync_reviewer_fields(config: dict) -> dict:
    active = active_reviewers(config)
    config.setdefault("reviewers", {})
    config["reviewers"].setdefault("available", reviewers_available(config))
    config["reviewers"]["active"] = active
    config["reviewers"].setdefault("presets", {})

    config.setdefault("routing", {})
    config["routing"]["review_requests_to"] = list(active)

    config.setdefault("gate", {})
    config["gate"]["require_approvals_from"] = list(active)

    config.setdefault("fan_in", {})
    config["fan_in"].setdefault("review", {})
    config["fan_in"]["review"]["required"] = list(active)
    return config


def current_task_id(task: dict | None) -> str:
    task = task or {}
    return str(task.get("task_id") or "").strip()


def hook_input(payload: dict) -> tuple[str, dict, dict, int]:
    tool_name = payload.get("tool_name") or payload.get("tool") or ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    tool_response = payload.get("tool_response") or payload.get("output") or {}
    exit_code = payload.get("exitCode", payload.get("exit_code", -1))
    return str(tool_name), dict(tool_input), dict(tool_response), int(exit_code) if isinstance(exit_code, int) else -1


def log_line(path: Path, message: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{timestamp()}] {message}"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def persist_session_runtime(project_root: Path, config: dict):
    orch_root, agents_root = resolve_shared_roots(config)
    runtime_dir = resolve_path("runtime_flags", project_root, config)
    runtime = {
        "project_root": str(project_root),
        "resolved_orchestrator_root": str(orch_root),
        "resolved_agents_root": str(agents_root),
        "resolved_at": timestamp(config),
        "hostname": platform.node(),
        "python": sys.version.split()[0],
    }
    write_json(runtime_dir / "session.json", runtime)
    return runtime


def compute_message_name(prefix: str, hint: str = "msg", config: dict | None = None) -> str:
    rnd = random.randint(1000, 9999)
    return f"{file_stamp(config)}-{prefix}-{sanitize(hint)}-{rnd}.md"
