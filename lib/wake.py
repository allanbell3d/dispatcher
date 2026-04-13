#!/usr/bin/env python3
"""
Wake wrapper for sleeping agents.

Source: MASTER_SPECS_MERGED.md section "Wake + injection mechanism (the core loop)"
and "Wake gotcha — flagged for round 1 verification".

Public API: wake_agent(name, mechanism, session_prefix) -> bool

Mechanism is swappable per spec F10. Current round 1 supports tmux and psmux.
Round 2+ may add other backends; add a new _wake_<mechanism> function and register
it in _MECHANISMS — no call-site changes required.

Empty-submission gotcha: tmux send-keys ENTER sends an empty string which Claude
Code may filter before firing UserPromptSubmit (REPL.tsx routing). Workaround:
send a single space + Enter. Consumers that read the resulting prompt should
strip leading whitespace before presenting to the user.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def wake_agent(name: str, mechanism: str = "tmux", session_prefix: str = "gate-") -> bool:
    """
    Wake a sleeping agent via the configured mechanism.

    Args:
        name: agent name from config.agents[].name (e.g. "coder-1")
        mechanism: wake mechanism — one of _MECHANISMS keys
        session_prefix: prefix prepended to agent name to form session name

    Returns:
        True if the wake subprocess succeeded (returncode 0), False otherwise.
        Returns False — never raises — for missing binary, timeout, or
        subprocess errors. Unsupported mechanism raises ValueError (caller bug).
    """
    if not name:
        _log_stderr(f"wake_agent: empty name, refusing to wake")
        return False

    impl = _MECHANISMS.get(mechanism)
    if impl is None:
        raise ValueError(
            f"wake_agent: unsupported mechanism '{mechanism}'. "
            f"Supported: {sorted(_MECHANISMS.keys())}"
        )

    target = f"{session_prefix}{name}"
    return impl(target)


def _wake_mux(binary: str, target: str) -> bool:
    """
    Common implementation for tmux/psmux send-keys wake.

    Sends a single space + Enter (the empty-submission workaround). Two
    separate subprocess calls — no shell string concatenation, no compound
    commands.
    """
    if shutil.which(binary) is None:
        _log_stderr(f"wake_agent: {binary} binary not found on PATH")
        return False

    try:
        rc1 = subprocess.run(
            [binary, "send-keys", "-t", target, " "],
            capture_output=True,
            text=True,
            timeout=5,
        ).returncode
        rc2 = subprocess.run(
            [binary, "send-keys", "-t", target, "Enter"],
            capture_output=True,
            text=True,
            timeout=5,
        ).returncode
    except FileNotFoundError:
        _log_stderr(f"wake_agent: {binary} disappeared between which() and run()")
        return False
    except subprocess.TimeoutExpired:
        _log_stderr(f"wake_agent: {binary} send-keys timed out for target {target}")
        return False
    except OSError as exc:
        _log_stderr(f"wake_agent: {binary} OSError: {exc}")
        return False

    if rc1 != 0 or rc2 != 0:
        _log_stderr(
            f"wake_agent: {binary} send-keys returned non-zero for target {target} "
            f"(space={rc1}, enter={rc2}) — session may not exist"
        )
        return False
    return True


def _wake_tmux(target: str) -> bool:
    return _wake_mux("tmux", target)


def _wake_psmux(target: str) -> bool:
    return _wake_mux("psmux", target)


def _log_stderr(msg: str) -> None:
    """Fail-soft logging. Wake failures must never cascade."""
    try:
        print(f"[wake] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


# Registry: add new mechanisms here, no call-site changes required
_MECHANISMS = {
    "tmux":  _wake_tmux,
    "psmux": _wake_psmux,
}
