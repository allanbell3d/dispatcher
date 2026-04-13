#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

"""
Inbox access guard -- PreToolUse hook.

Source: MASTER_SPECS_MERGED.md
  - Hard rules #5: "The coder NEVER sees the plan. [...] state_root is
    agent-prohibited, inbox-access-guard blocks any Read/Grep/Glob/Bash
    against it."
  - Access model three tiers: engine-private / agent-facing / shared-writable.
  - Components #6: "PreToolUse hook denies state_root/* and dispatch/<other>/*"

Behavior:
  - Reads GATE_AGENT_NAME from env (permissive fallback if unset).
  - Reads hook input JSON from stdin.
  - Extracts target path(s) from tool_input:
      Read=file_path, Grep=path, Glob=path, Bash=command string (all path tokens).
  - DENIES if:
      (a) target under state_root/* (engine-private)
      (b) target under dispatch/<other_agent>/* where other != self
  - Pathless Grep/Glob/Bash from a stamped agent are also denied (spec Q6).
  - ALLOWS everything else (project source, own dispatch folder, external files).
  - Reviewer/monitor exceptions (spec F7a/F7b) are TODO -- round 1 default denies
    state_root for everyone; config-driven exceptions land in a later wave.

Output schema: matches check_gate.py pattern -- decision + reason via stdout JSON.
"""
import json
import os
import re
import time as _time

from lib.common import hook_input, load_project_config, resolve_path, resolve_project_root, trace_hook


ALLOW = {}
PROTECTED_TOOLS = {"Read", "Grep", "Glob", "Bash"}

# Regex to extract path-like tokens from a Bash command string.
# Matches sequences that look like filesystem paths (contain a slash).
# Match path tokens with forward OR backslash (Windows-safe per Rule #9).
_PATH_TOKEN_RE = re.compile(
    r"(?:[A-Za-z]:[/\\][\w./\\-]+|[.~]?[/\\][\w./\\-]+|[\w.-]+[/\\][\w./\\-]+)"
)


def _deny(reason: str):
    print(json.dumps({"decision": "deny", "reason": reason}))
    print(reason, file=sys.stderr)
    sys.exit(2)


def _extract_target_paths(tool_name: str, tool_input: dict) -> list:
    """
    Tool-specific target path extraction. Returns a list of candidate paths.

    Read:  file_path (single)
    Grep:  path (may be None -> empty list)
    Glob:  path (may be None -> empty list)
    Bash:  all path-like tokens in command string
    """
    if tool_name == "Read":
        v = str(tool_input.get("file_path", ""))
        return [v] if v else []
    if tool_name in ("Grep", "Glob"):
        v = str(tool_input.get("path", "") or "")
        return [v] if v else []
    if tool_name == "Bash":
        cmd = str(tool_input.get("command", ""))
        return _PATH_TOKEN_RE.findall(cmd)
    return []


def _is_under(target: Path, root: Path) -> bool:
    """
    Windows-safe subpath check. Returns True if target is under root.
    Uses resolved paths to handle .. and symlinks; falls back to string
    prefix if resolve() fails (e.g., file does not exist yet).
    """
    try:
        target_r = target.resolve()
        root_r = root.resolve()
    except (OSError, ValueError):
        target_r = target
        root_r = root
    try:
        target_r.relative_to(root_r)
        return True
    except ValueError:
        return False


def main() -> int:
    _t0 = _time.monotonic()
    if not os.environ.get("GATE_AGENT_NAME", "").strip():
        trace_hook(hook="inbox_access_guard", agent="", decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="no agent")
        print(json.dumps(ALLOW))
        return 0

    from lib.common import is_hook_disabled
    if is_hook_disabled("inbox_access_guard"):
        trace_hook(hook="inbox_access_guard", agent=os.environ.get("GATE_AGENT_NAME", "").strip(),
                   decision="allow", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="hook disabled")
        print(json.dumps(ALLOW))
        return 0

    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        agent = os.environ.get("GATE_AGENT_NAME", "").strip()
        trace_hook(hook="inbox_access_guard", agent=agent, decision="deny",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="malformed stdin")
        _deny("Malformed hook payload")

    tool_name, tool_input, _, _ = hook_input(payload)
    if tool_name not in PROTECTED_TOOLS:
        trace_hook(hook="inbox_access_guard", agent=os.environ.get("GATE_AGENT_NAME", "").strip(),
                   decision="allow", elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   tool=tool_name, reason="tool not protected")
        print(json.dumps(ALLOW))
        return 0

    agent = os.environ.get("GATE_AGENT_NAME", "").strip()

    try:
        project_root_early = resolve_project_root()
        config_early = load_project_config(project_root_early)
    except Exception:
        project_root_early = None
        config_early = None

    target_strs = _extract_target_paths(tool_name, tool_input)

    if not target_strs:
        # No path given (e.g., Glob with pattern only, cwd-based).
        # For stamped agents, pathless Grep/Glob/Bash are denied -- they
        # bypass the explicit-path guard and could hit engine-private dirs.
        if agent and tool_name in ("Grep", "Glob", "Bash"):
            trace_hook(hook="inbox_access_guard", agent=agent, decision="deny",
                       elapsed_ms=(_time.monotonic() - _t0) * 1000,
                       project_root=None, config=None,
                       reason="pathless search denied", tool=tool_name)
            _deny(
                "Pathless search/command denied for gated agents -- specify an "
                "explicit path outside state_root."
            )
        # Unstamped session (Allan's own) -- allow.
        print(json.dumps(ALLOW))
        return 0

    if not agent:
        # Permissive fallback: unstamped sessions (Allan's own) are allowed.
        # Agents must be explicitly stamped to be restricted.
        trace_hook(hook="inbox_access_guard", agent="", decision="allow",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="no agent after extraction")
        print(json.dumps(ALLOW))
        return 0

    try:
        project_root = resolve_project_root()
        config = load_project_config(project_root)
    except Exception as exc:
        trace_hook(hook="inbox_access_guard", agent=agent, decision="deny",
                   elapsed_ms=(_time.monotonic() - _t0) * 1000,
                   reason="config unavailable", error=str(exc))
        _deny(f"Cannot resolve project config: {exc}")

    # (a) engine-private tier: state_root/* -- denied for ALL agents.
    # TODO(F7a/F7b): Before Wave 3 -- add config-driven exceptions for reviewers
    # (diffs/<task>.diff, specs/*) and monitors (audit.log read, halt write).
    # See spec FLAGs F7a, F7b.
    state_root = resolve_path("state_root", project_root, config)

    # (b) agent-facing tier: dispatch/<other>/* -- denied cross-agent.
    dispatch_root = resolve_path("dispatch_root", project_root, config)

    for target_str in target_strs:
        if not target_str:
            continue
        target = Path(target_str)
        if not target.is_absolute():
            target = (project_root / target).resolve()

        if _is_under(target, state_root):
            reason = (
                f"Path is read-only for role '{agent}'. "
                f"state_root is engine-private (spec hard rule #5)."
            )
            trace_hook(hook="inbox_access_guard", agent=agent, decision="deny",
                       elapsed_ms=(_time.monotonic() - _t0) * 1000,
                       project_root=project_root, config=config,
                       reason="state_root access", tool=tool_name)
            _deny(reason)

        if _is_under(target, dispatch_root):
            # Target is under dispatch/ -- check which agent subtree.
            try:
                rel = target.relative_to(dispatch_root.resolve())
                owner = rel.parts[0] if rel.parts else ""
            except (ValueError, OSError):
                owner = ""
            if owner and owner != agent:
                reason = (
                    f"Path is read-only for role '{agent}'. "
                    f"dispatch/{owner}/* belongs to another agent."
                )
                trace_hook(hook="inbox_access_guard", agent=agent, decision="deny",
                           elapsed_ms=(_time.monotonic() - _t0) * 1000,
                           project_root=project_root, config=config,
                           reason="cross-agent dispatch", tool=tool_name, owner=owner)
                _deny(reason)

    # Everything else: project source, external files, own dispatch subtree.
    trace_hook(hook="inbox_access_guard", agent=agent, decision="allow",
               elapsed_ms=(_time.monotonic() - _t0) * 1000,
               project_root=project_root, config=config,
               tool=tool_name)
    print(json.dumps(ALLOW))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        print("BLOCKED: Hook error — blocked for safety", file=sys.stderr)
        sys.exit(2)
