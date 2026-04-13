#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import ast
import json
import re

from lib.common import agent_names, load_project_config, read_json, resolve_path, resolve_project_root, resolve_shared_roots

LIVE_PATTERNS = [
    ".orchestrator/config.json",
    ".orchestrator/tasks/*.json",
    "docs/**/*.md",
]

def compile_python(paths: list[Path]) -> list[str]:
    errors = []
    for path in paths:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"python syntax error in {path}: {exc}")
    return errors

_TYPE_MAP = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}

def _schema_errors(value, schema: dict, path: str) -> list[str]:
    """Recursively validate *value* against a hand-rolled JSON Schema node."""
    errs: list[str] = []
    expected_type = schema.get("type")

    # Type check — bool guard must come first (Python bool subclasses int)
    if expected_type == "integer" and isinstance(value, bool):
        errs.append(f"{path}: expected integer, got boolean")
        return errs
    if expected_type and expected_type in _TYPE_MAP:
        if not isinstance(value, _TYPE_MAP[expected_type]):
            errs.append(
                f"{path}: expected {expected_type}, got {type(value).__name__}"
            )
            return errs

    # Enum check
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: value {value!r} not in allowed values {schema['enum']}")

    # Object — required keys, additionalProperties, recurse into properties
    if expected_type == "object" and isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}.{req}: required key missing")
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    errs.append(f"{path}.{k}: unknown key (additionalProperties: false)")
        for k, sub_schema in props.items():
            if k in value:
                errs.extend(_schema_errors(value[k], sub_schema, f"{path}.{k}"))

    # Array — minItems, items schema
    if expected_type == "array" and isinstance(value, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errs.append(f"{path}: array has {len(value)} items, minimum is {min_items}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                errs.extend(_schema_errors(item, item_schema, f"{path}[{i}]"))

    return errs


def validate_config(config: dict, schema: dict, config_agent_names: list[str], warnings: list[str] | None = None) -> list[str]:
    """A4 — hand-rolled config schema validator. No jsonschema pip package."""
    errors: list[str] = []

    # Walk schema
    errors.extend(_schema_errors(config, schema, "config"))

    # Cross-reference agent names: every agent name referenced in routing/gate/fan_in
    # must exist in agents[].name
    agent_set = set(config_agent_names)

    def _check_agent_refs(names, location: str) -> None:
        if not isinstance(names, list):
            return
        for name in names:
            if isinstance(name, str) and name not in agent_set:
                errors.append(
                    f"config: {location} references unknown agent {name!r} "
                    f"(not in agents[].name)"
                )

    gate = config.get("gate", {})
    _check_agent_refs(gate.get("require_approvals_from"), "gate.require_approvals_from")

    routing = config.get("routing", {})
    for key in (
        "review_requests_to",
        "cc_all",
        "on_batch_complete",
        "on_test_failure",
        "on_test_passed",
        "on_stop",
    ):
        _check_agent_refs(routing.get(key), f"routing.{key}")

    fan_in_required = config.get("fan_in", {}).get("review", {}).get("required")
    _check_agent_refs(fan_in_required, "fan_in.review.required")

    esc = routing.get("escalation_target")
    if esc and isinstance(esc, str) and esc not in agent_set:
        if warnings is not None:
            warnings.append(
                f"config: routing.escalation_target references {esc!r} "
                f"which is not in agents[].name (may be intentional for human escalation)"
            )

    return errors


_FORBIDDEN_PLACEHOLDERS = re.compile(r"\b(TODO|TBD|PLACEHOLDER|FIXME|XXX)\b")


def validate_plans(project_root, config: dict) -> list[str]:
    """H3 — thorough plan format validator."""
    errors: list[str] = []
    plans_dir = resolve_path("plans", project_root, config)

    if not plans_dir.is_dir():
        return errors  # skip silently

    plan_files = sorted(plans_dir.glob("*.json"))
    if not plan_files:
        return errors  # skip silently

    for plan_file in plan_files:
        data = read_json(plan_file, None)
        if not isinstance(data, dict):
            errors.append(f"plan {plan_file.name}: must be a JSON object")
            continue

        if "plan_id" not in data and "tasks" not in data:
            continue

        label = plan_file.name

        # Required top-level keys
        for key in ("plan_id", "tasks"):
            if key not in data:
                errors.append(f"plan {label}: missing required key '{key}'")

        tasks = data.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            errors.append(f"plan {label}: 'tasks' must be a non-empty list")
            continue

        for idx, task in enumerate(tasks, 1):
            if not isinstance(task, dict):
                errors.append(f"plan {label} task #{idx}: must be an object")
                continue

            task_id = task.get("task_id", f"#{idx}")

            # Required task keys
            for key in ("task_id", "title", "acceptance_criteria", "reference_paths"):
                if key not in task:
                    errors.append(
                        f"plan {label} task {task_id}: missing required key '{key}'"
                    )

            # acceptance_criteria — non-empty list of strings
            ac = task.get("acceptance_criteria")
            if not isinstance(ac, list) or not ac:
                errors.append(
                    f"plan {label} task {task_id}: acceptance_criteria must be a non-empty list"
                )
            else:
                for ac_idx, criterion in enumerate(ac, 1):
                    if not isinstance(criterion, str):
                        errors.append(
                            f"plan {label} task {task_id} AC#{ac_idx}: must be a string"
                        )
                    elif _FORBIDDEN_PLACEHOLDERS.search(criterion):
                        match = _FORBIDDEN_PLACEHOLDERS.search(criterion)
                        errors.append(
                            f"plan {label} task {task_id} AC#{ac_idx}: "
                            f"forbidden placeholder {match.group()!r} in criterion: {criterion!r}"
                        )

            # reference_paths — must be a list
            rp = task.get("reference_paths")
            if rp is not None and not isinstance(rp, list):
                errors.append(
                    f"plan {label} task {task_id}: reference_paths must be a list"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate project + orchestrator contract")
    parser.add_argument("project", nargs="?", default=None)
    args = parser.parse_args()

    project_root = resolve_project_root(args.project)
    config = load_project_config(project_root)
    orch_root, _ = resolve_shared_roots(config)

    errors: list[str] = []
    warnings: list[str] = []

    # required dirs/files — spec keys only (MASTER_SPECS_MERGED.md "Config shape")
    for key in ["dispatch_root", "state_root", "tasks", "current_task", "plans"]:
        p = resolve_path(key, project_root, config)
        if not p.exists():
            errors.append(f"missing required path ({key}): {p}")

    # agent contract
    dispatch_root = resolve_path("dispatch_root", project_root, config)
    for agent in agent_names(config):
        for sub in ["inbox", "outbox", "reports", "done", "archive"]:
            if not (dispatch_root / agent / sub).exists():
                errors.append(f"dispatch folder missing: dispatch/{agent}/{sub}")

    # task / plan format
    tasks_dir = resolve_path("tasks", project_root, config)
    current_task_path = resolve_path("current_task", project_root, config)
    plans_dir = resolve_path("plans", project_root, config)

    # Read tasks from directory listing of .json files
    task_files = sorted(tasks_dir.glob("*.json")) if tasks_dir.is_dir() else []
    tasks = []
    for tf in task_files:
        if tf.name == Path(current_task_path).name:
            continue
        data = read_json(tf, None)
        if isinstance(data, list):
            tasks.extend(data)
        elif isinstance(data, dict):
            tasks.append(data)

    current = read_json(current_task_path, {})

    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks must be a non-empty list (from tasks directory .json files)")
    else:
        ids = set()
        for idx, item in enumerate(tasks, 1):
            for key in ["task_id", "title"]:
                if key not in item or not item.get(key):
                    errors.append(f"task #{idx} missing {key}")
            ac = item.get("acceptance_criteria")
            if not isinstance(ac, list) or not ac:
                errors.append(f"task #{idx} acceptance_criteria must be a non-empty list")
            rp = item.get("reference_paths")
            if not isinstance(rp, list):
                errors.append(f"task #{idx} reference_paths must be a list")
            if item.get("task_id") in ids:
                errors.append(f"duplicate task id: {item.get('task_id')}")
            ids.add(item.get("task_id"))
        if current and current.get("task_id") not in ids:
            errors.append(f"current task {current.get('task_id')} not present in tasks")
    # H3 — plan format validator (replaces basic plan check above)
    errors.extend(validate_plans(project_root, config))

    # A4 — config schema validator
    schema_path = ROOT / "schemas" / "config_schema.json"
    if schema_path.exists():
        schema = read_json(schema_path, {})
        errors.extend(validate_config(config, schema, agent_names(config), warnings))
    else:
        errors.append(f"config_schema.json not found: {schema_path}")

    # forbidden patterns
    forbidden = [(item["pattern"], item["label"]) for item in config.get("forbidden_patterns", []) if isinstance(item, dict) and item.get("pattern")]
    scanned = set()
    for pattern in LIVE_PATTERNS:
        scanned.update(project_root.glob(pattern))
    scanned.update((orch_root / "scripts").glob("*.py"))
    scanned.update((orch_root / "hooks").glob("*.py"))
    # mcp-server/server.ts omitted — MCP is frozen (spec Rule #20: do not wire, do not reference as available)
    # scanned.add(orch_root / "mcp-server" / "server.ts")
    for path in sorted(scanned):
        if not path.exists() or path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        config_path = project_root / ".orchestrator" / "config.json"
        if path == config_path:
            continue
        for patt, label in forbidden:
            if re.search(patt, text):
                errors.append(f"{label} still present in {path}")

    # scripts presence + syntax
    expected = [
        orch_root / "scripts" / "watcher.py",
        orch_root / "scripts" / "send.py",
        orch_root / "scripts" / "validate.py",
        orch_root / "scripts" / "doctor.py",
        orch_root / "scripts" / "install_hooks.py",
        orch_root / "hooks" / "check_gate.py",
        orch_root / "hooks" / "dispatch_next_bug.py",
        orch_root / "hooks" / "activity_logger.py",
        orch_root / "hooks" / "on_file_message.py",
        orch_root / "hooks" / "dispatch_gate.py",
        orch_root / "hooks" / "inbox_access_guard.py",
        orch_root / "hooks" / "monitor_ingest.py",
        orch_root / "hooks" / "stop_notify.py",
        # mcp-server/server.ts omitted — MCP is frozen (spec Rule #20: do not wire, do not reference as available)
    ]
    for path in expected:
        if not path.exists():
            errors.append(f"missing orchestrator file: {path}")

    errors.extend(compile_python(list((orch_root / "scripts").glob("*.py")) + list((orch_root / "hooks").glob("*.py")) + list((orch_root / "lib").glob("*.py"))))

    if warnings:
        for msg in warnings:
            print(f"WARN: {msg}")
    if errors:
        for msg in errors:
            print(f"ERROR: {msg}")
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: PASS — validated {project_root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
