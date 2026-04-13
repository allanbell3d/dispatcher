from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_entrypoint(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def assert_no_bootstrap_import_error(result: subprocess.CompletedProcess[str]) -> None:
    combined = f"{result.stdout}\n{result.stderr}"
    assert "ModuleNotFoundError" not in combined


def test_hook_entrypoints_import_from_repo_root() -> None:
    for hook_path in (
        REPO_ROOT / "hooks" / "dispatch_gate.py",
        REPO_ROOT / "hooks" / "activity_logger.py",
    ):
        result = run_entrypoint(str(hook_path))
        assert result.returncode == 0, result.stderr
        assert_no_bootstrap_import_error(result)


def test_script_entrypoint_import_from_repo_root() -> None:
    result = run_entrypoint(str(REPO_ROOT / "scripts" / "doctor.py"), "--help")
    assert result.returncode == 0, result.stderr
    assert_no_bootstrap_import_error(result)
