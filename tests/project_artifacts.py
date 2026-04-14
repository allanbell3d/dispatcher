#!/usr/bin/env python3
"""Helpers for building test projects from the canonical artifact library."""

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def artifact_json(relative: str) -> dict | list:
    return json.loads((ARTIFACTS / relative).read_text(encoding="utf-8"))


def build_project(project: Path, *, project_name: str) -> dict:
    config = copy.deepcopy(artifact_json("install/config/config.seed.json"))
    config["project"] = project_name
    for key in ("orchestrator_primary", "orchestrator_fallback", "agents_primary", "agents_fallback"):
        config["shared_roots"][key] = str(ROOT)

    paths = config["paths"]
    for key in ("plans", "tasks", "diffs", "merged_verdicts", "halts", "runtime_flags", "logs"):
        (project / paths[key]).mkdir(parents=True, exist_ok=True)

    dispatch_root = project / paths["dispatch_root"]
    for agent in config["agents"]:
        for subdir in ("inbox", "outbox", "reports", "done", "archive"):
            (dispatch_root / agent["name"] / subdir).mkdir(parents=True, exist_ok=True)

    (project / paths["state_root"] / "config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )
    return config


def write_artifact_json(project: Path, target_relative: str, artifact_relative: str, *, overrides: dict | None = None) -> None:
    payload = copy.deepcopy(artifact_json(artifact_relative))
    if overrides:
        payload.update(overrides)
    (project / target_relative).write_text(json.dumps(payload, indent=2), encoding="utf-8")
