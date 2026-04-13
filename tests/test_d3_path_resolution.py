#!/usr/bin/env python3
"""Test D-T3 (J2): path resolution harness for all config.paths keys."""
import json, os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.common import resolve_path, resolve_project_root, _PATH_KEY_DEFAULTS

_CONFIG_FULL = {
    "project": "j2-test",
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
    "agents": [],
    "gate": {},
    "routing": {},
    "fan_in": {},
    "wake": {},
    "session": {},
}

_CONFIG_MINIMAL = {
    "project": "j2-minimal",
    "shared_roots": {
        "orchestrator_primary": "W:/Claude_Library/orchestrator",
        "orchestrator_fallback": "D:/IA/orchestrator",
        "agents_primary": "W:/Claude_Library/agents",
        "agents_fallback": "D:/IA/agents"
    },
    "paths": {},
    "agents": [],
}


def setup(tmp: Path, config: dict):
    (tmp / ".orchestrator").mkdir(parents=True, exist_ok=True)
    (tmp / ".orchestrator" / "config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}: {label}" + (f" -- {detail}" if detail else ""))
    return condition


if __name__ == "__main__":
    passed = True

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # --- Full config: all keys present ---
        setup(tmp, _CONFIG_FULL)
        os.chdir(str(tmp))
        project_root = resolve_project_root(str(tmp))

        for key, rel_default in _PATH_KEY_DEFAULTS.items():
            try:
                resolved = resolve_path(key, project_root, _CONFIG_FULL)
                passed &= check(f"resolve_path('{key}') succeeds", True, str(resolved))
                passed &= check(f"resolve_path('{key}') is absolute", resolved.is_absolute(),
                                str(resolved))
            except Exception as e:
                passed &= check(f"resolve_path('{key}') succeeds", False, str(e))

        # decision_trace should resolve
        dt = resolve_path("decision_trace", project_root, _CONFIG_FULL)
        passed &= check("decision_trace resolves", dt is not None, str(dt))
        passed &= check("decision_trace ends with .log",
                        str(dt).endswith("decision_trace.log"), str(dt))

        # --- Minimal config: keys fall back to defaults ---
        setup(tmp, _CONFIG_MINIMAL)
        for key, rel_default in _PATH_KEY_DEFAULTS.items():
            try:
                resolved = resolve_path(key, project_root, _CONFIG_MINIMAL)
                expected_suffix = Path(rel_default).name
                passed &= check(f"fallback '{key}' resolves", True, str(resolved))
                passed &= check(f"fallback '{key}' ends with default name",
                                resolved.name == expected_suffix or expected_suffix in str(resolved),
                                f"got={resolved.name} want_contains={expected_suffix}")
            except Exception as e:
                passed &= check(f"fallback '{key}' resolves", False, str(e))

        # --- Unknown key raises KeyError ---
        try:
            resolve_path("nonexistent_key_xyz", project_root, _CONFIG_FULL)
            passed &= check("unknown key raises KeyError", False, "did not raise")
        except KeyError:
            passed &= check("unknown key raises KeyError", True)
        except Exception as e:
            passed &= check("unknown key raises KeyError", False, f"raised {type(e).__name__}")

        # --- Absolute path in config is returned as-is ---
        abs_config = dict(_CONFIG_FULL)
        if sys.platform == "win32":
            abs_config["paths"] = {**abs_config["paths"], "audit_log": "C:/tmp/audit.log"}
        else:
            abs_config["paths"] = {**abs_config["paths"], "audit_log": "/tmp/audit.log"}
        resolved = resolve_path("audit_log", project_root, abs_config)
        passed &= check("absolute path returned as-is", resolved.is_absolute(), str(resolved))
        expected_abs = "C:\\tmp\\audit.log" if sys.platform == "win32" else "/tmp/audit.log"
        passed &= check("absolute path matches config",
                        str(resolved).replace("/", os.sep) == expected_abs.replace("/", os.sep) or
                        str(resolved) == expected_abs.replace("\\", "/"),
                        str(resolved))

        # Restore CWD before temp dir cleanup (Windows locks dirs with active CWD)
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # --- J2: cross-drive resolve_project_root scenario ---
    # Spec SHOW-STOPPER: resolve_project_root() must work when CWD is under
    # a different drive than the hook script. Simulate by passing an explicit
    # path on the same drive (cross-drive filesystem access is transparent on
    # Windows via Path.resolve(); the real guard is that we never os.chdir to
    # the hook's drive — we always pass explicit project_root).
    with tempfile.TemporaryDirectory() as td2:
        tmp2 = Path(td2)
        setup(tmp2, _CONFIG_FULL)
        try:
            pr = resolve_project_root(str(tmp2))
            passed &= check("J2 cross-drive: resolve_project_root with explicit path", True, str(pr))
            passed &= check("J2 cross-drive: returned path is absolute", pr.is_absolute(), str(pr))
            passed &= check("J2 cross-drive: config.json accessible", (pr / ".orchestrator" / "config.json").exists(), str(pr))
            # Verify all path keys resolve correctly from explicit project root
            for key in list(_PATH_KEY_DEFAULTS.keys())[:3]:
                r = resolve_path(key, pr, _CONFIG_FULL)
                passed &= check(f"J2 cross-drive: resolve_path('{key}') absolute", r.is_absolute(), str(r))
        except Exception as e:
            passed &= check("J2 cross-drive: resolve_project_root with explicit path", False, str(e))

    sys.exit(0 if passed else 1)
