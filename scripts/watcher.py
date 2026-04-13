#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import threading
import time
from dataclasses import dataclass, asdict, field

from lib.common import (
    atomic_write,
    audit_log,
    compute_message_name,
    ensure_dispatch_dirs,
    load_project_config,
    persist_session_runtime,
    read_json,
    resolve_path,
    resolve_project_root,
    sort_files_by_mtime,
    timestamp,
    trace_hook,
    write_json,
)
from lib.wake import wake_agent

@dataclass
class FanInTracker:
    request_id: str
    msg_type: str
    sender: str
    required: list[str]
    timeout_seconds: int
    on_timeout: str
    original_body: str
    created_at: float = field(default_factory=time.time)
    received: dict[str, str] = field(default_factory=dict)
    escalated: bool = False

    def is_complete(self) -> bool:
        return set(self.required).issubset(self.received.keys())

    def is_timed_out(self) -> bool:
        return (time.time() - self.created_at) > self.timeout_seconds

    def missing(self) -> list[str]:
        return sorted(set(self.required) - set(self.received))


def parse_message(content: str) -> dict:
    content = content.strip()
    headers, body = (content.split("---", 1) + [""])[:2] if "---" in content else ("", content)
    data = {"from": "", "to": [], "type": "", "task_id": "", "verdict": "", "body": body.strip()}
    for raw in headers.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()
        if key == "FROM":
            data["from"] = value
        elif key == "TO":
            data["to"] = [x.strip() for x in value.split(",") if x.strip()]
        elif key == "TYPE":
            data["type"] = value.lower()
        elif key == "TASK_ID":
            data["task_id"] = value
        elif key == "VERDICT":
            data["verdict"] = value.lower()
    return data


def compose_message(config: dict, sender: str, recipients: list[str], msg_type: str, task_id: str, body: str, verdict: str = "") -> str:
    lines = [f"FROM: {sender}"]
    if recipients:
        lines.append("TO: " + ", ".join(recipients))
    if msg_type:
        lines.append(f"TYPE: {msg_type}")
    if task_id:
        lines.append(f"TASK_ID: {task_id}")
    if verdict:
        lines.append(f"VERDICT: {verdict}")
    lines.append(f"TIMESTAMP: {timestamp(config)}")
    lines.extend(["---", body.strip(), ""])
    return "\n".join(lines)

def write_message(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, content)

def move_file(src: Path, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / src.name
    if target.exists():
        target = dest_dir / f"{src.stem}-{int(time.time())}{src.suffix}"
    src.replace(target)


def save_trackers(path: Path, trackers: dict[str, FanInTracker]):
    payload = {k: asdict(v) for k, v in trackers.items()}
    write_json(path, payload)

def load_trackers(path: Path) -> dict[str, FanInTracker]:
    data = read_json(path, {})
    trackers: dict[str, FanInTracker] = {}
    if isinstance(data, dict):
        for key, item in data.items():
            try:
                trackers[key] = FanInTracker(**item)
            except TypeError:
                continue
    return trackers

def liveness_check_once(
    agent_names: list,
    dispatch_root: Path,
    ltu_dir: Path,
    idle_threshold_seconds: int,
    retry_interval_seconds: int,
    wake_cooldowns: dict,
    project_root: Path = None,
    config: dict = None,
) -> list:
    """Run one liveness check pass. Returns list of agent names to wake.

    Core rule: only wake agents with unread inbox items AND idle time > threshold.
    Missing last_tool_use file = skip (agent never started).
    .tmp files in inbox don't count.
    Cooldown: don't re-wake within retry_interval_seconds.
    """
    import time as _time
    _start = _time.monotonic()
    now = time.time()
    to_wake = []

    for agent in agent_names:
        ltu_file = ltu_dir / f"{agent}.ts"

        # Missing ltu file = agent never started, skip
        if not ltu_file.exists():
            trace_hook(hook="liveness", agent=agent, decision="skip",
                       elapsed_ms=round((_time.monotonic() - _start) * 1000),
                       project_root=project_root, config=config,
                       reason="no last_tool_use file")
            continue

        # Read last activity timestamp
        try:
            last_active = float(ltu_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            trace_hook(hook="liveness", agent=agent, decision="skip",
                       elapsed_ms=round((_time.monotonic() - _start) * 1000),
                       project_root=project_root, config=config,
                       reason="unreadable ltu file")
            continue

        idle_seconds = now - last_active
        is_idle = idle_seconds > idle_threshold_seconds

        if not is_idle:
            trace_hook(hook="liveness", agent=agent, decision="skip",
                       elapsed_ms=round((_time.monotonic() - _start) * 1000),
                       project_root=project_root, config=config,
                       reason="agent active", idle_seconds=round(idle_seconds, 1))
            continue

        # Check inbox for real (non-.tmp) files
        inbox_dir = dispatch_root / agent / "inbox"
        try:
            inbox_files = [
                p for p in inbox_dir.iterdir()
                if p.is_file() and p.suffix != ".tmp"
            ] if inbox_dir.is_dir() else []
        except OSError:
            inbox_files = []

        if not inbox_files:
            trace_hook(hook="liveness", agent=agent, decision="skip",
                       elapsed_ms=round((_time.monotonic() - _start) * 1000),
                       project_root=project_root, config=config,
                       reason="idle but inbox empty",
                       idle_seconds=round(idle_seconds, 1))
            continue

        # Check cooldown
        last_wake = wake_cooldowns.get(agent, 0)
        if (now - last_wake) < retry_interval_seconds:
            trace_hook(hook="liveness", agent=agent, decision="skip",
                       elapsed_ms=round((_time.monotonic() - _start) * 1000),
                       project_root=project_root, config=config,
                       reason="cooldown active",
                       idle_seconds=round(idle_seconds, 1),
                       cooldown_remaining=round(retry_interval_seconds - (now - last_wake), 1))
            continue

        # Agent is idle AND has unread inbox AND cooldown expired -> wake
        trace_hook(hook="liveness", agent=agent, decision="wake",
                   elapsed_ms=round((_time.monotonic() - _start) * 1000),
                   project_root=project_root, config=config,
                   idle_seconds=round(idle_seconds, 1),
                   inbox_count=len(inbox_files))
        wake_cooldowns[agent] = now
        to_wake.append(agent)

    return to_wake


def liveness_ticker_thread(
    agent_names: list,
    dispatch_root: Path,
    ltu_dir: Path,
    wake_cfg: dict,
    stop_file: Path,
    wake_mechanism: str,
    session_prefix: str,
    project_root: Path,
    config: dict,
    log_fn,
):
    """Daemon thread: periodically checks agent liveness and wakes stale agents."""
    interval = int(wake_cfg.get("liveness_check_interval_seconds", 30))
    idle_threshold = int(wake_cfg.get("idle_threshold_seconds", 120))
    retry_interval = int(wake_cfg.get("retry_interval_seconds", 10))
    wake_cooldowns: dict = {}

    while not stop_file.exists():
        try:
            to_wake = liveness_check_once(
                agent_names=agent_names,
                dispatch_root=dispatch_root,
                ltu_dir=ltu_dir,
                idle_threshold_seconds=idle_threshold,
                retry_interval_seconds=retry_interval,
                wake_cooldowns=wake_cooldowns,
                project_root=project_root,
                config=config,
            )
            for agent in to_wake:
                ok = wake_agent(agent, wake_mechanism, session_prefix)
                if ok:
                    log_fn(f"LIVENESS WAKE: {agent}")
                else:
                    log_fn(f"LIVENESS WAKE FAILED: {agent} (mechanism={wake_mechanism})")
        except Exception as exc:
            try:
                log_fn(f"LIVENESS ERROR: {exc}")
            except Exception:
                pass
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the orchestrator watcher")
    parser.add_argument("project", nargs="?", default=None)
    args = parser.parse_args()

    project_root = resolve_project_root(args.project)
    config = load_project_config(project_root)
    persist_session_runtime(project_root, config)
    dispatch_dir = resolve_path("dispatch_root", project_root, config)

    log_path = resolve_path("logs", project_root, config) / "watcher.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    def log(msg: str):
        line = f"[{timestamp(config)}] {msg}"
        print(line, flush=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    tracker_path = resolve_path("trackers", project_root, config)
    stop_file = resolve_path("runtime_flags", project_root, config) / "STOP"
    session_prefix = config.get("session", {}).get("session_prefix", "gate-")
    wake_cfg = config.get("wake", {})
    first_attempt_seconds = int(wake_cfg.get("first_attempt_seconds", 15))
    retry_interval_seconds = int(wake_cfg.get("retry_interval_seconds", 10))
    max_retries = int(wake_cfg.get("max_retries", 30))
    pulse_interval_seconds = int(wake_cfg.get("monitor_pulse_seconds", 30))
    require_ready = bool(config.get("session", {}).get("require_ready_files", False))

    escalation_target = config.get("routing", {}).get("escalation_target", "")

    agent_names = [a.get("name") for a in config.get("agents", []) if a.get("name")]
    for agent in [*agent_names, *([escalation_target] if escalation_target else [])]:
        ensure_dispatch_dirs(dispatch_dir, agent)

    trackers = load_trackers(tracker_path)
    pending_wakes: dict[str, dict] = {}
    monitor_buffer: list[str] = []
    last_pulse = time.time()
    wake_mechanism = config.get("wake", {}).get("mechanism", "tmux")

    def queue_wake(agent: str, preview: str):
        pending_wakes[agent] = {
            "delivered_at": time.time(),
            "last_retry_at": 0.0,
            "retries": 0,
            "first_sent": False,
            "preview": preview[:500],
        }

    def valid_recipients(parsed: dict) -> list[str]:
        recipients = set(parsed.get("to", []))
        msg_type = parsed.get("type", "")
        routing = config.get("routing", {})
        if msg_type:
            recipients.update(routing.get(f"on_{msg_type}", []))
        recipients.update(routing.get("cc_all", []))
        sender = parsed.get("from", "")
        recipients.discard(sender)
        return [r for r in sorted(recipients) if r]

    def deliver_message(sender: str, parsed: dict, source_file: Path, direct_to: list[str] | None = None):
        recipients = direct_to or valid_recipients(parsed)
        task_id = parsed.get("task_id") or source_file.stem
        body = parsed.get("body", "")
        msg_type = parsed.get("type", "direct_message") or "direct_message"
        verdict = parsed.get("verdict", "")
        content = compose_message(config, sender, recipients, msg_type, task_id, body, verdict)
        fan_in_cfg = config.get("fan_in", {}).get(msg_type)
        for recipient in recipients:
            if require_ready and recipient != escalation_target:
                ready = dispatch_dir / recipient / "ready"
                if not ready.exists():
                    log(f"DEFER {source_file.name}: {recipient} not ready")
                    continue
            ensure_dispatch_dirs(dispatch_dir, recipient)
            target = dispatch_dir / recipient / "inbox" / compute_message_name(f"from-{sender}", task_id or recipient, config)
            write_message(target, content)
            queue_wake(recipient, content)
            log(f"DELIVER {source_file.name}: {sender} -> {recipient} ({msg_type})")
            monitor_buffer.append(f"{sender} -> {recipient} ({msg_type}) {task_id}")
        if fan_in_cfg and recipients:
            trackers[task_id] = FanInTracker(
                request_id=task_id,
                msg_type=msg_type,
                sender=sender,
                required=list(fan_in_cfg.get("required", recipients)),
                timeout_seconds=int(fan_in_cfg.get("timeout_seconds", 300)),
                on_timeout=str(fan_in_cfg.get("on_timeout", "escalate_allan")),
                original_body=body,
            )
            save_trackers(tracker_path, trackers)
            log(f"FAN-IN START {task_id}: waiting for {trackers[task_id].required}")

    def handle_review_request(sender: str, parsed: dict, source_file: Path) -> bool:
        """
        Explicit fan-out for TYPE: review_request messages.

        Routes to config.routing.review_requests_to (explicit reviewer list)
        and CC-copies to config.routing.cc_all, then starts a fan-in tracker.
        Returns True so the caller skips the generic deliver_message() path.
        """
        routing = config.get("routing", {})
        reviewers = routing.get("review_requests_to", [])
        cc_targets = routing.get("cc_all", [])
        task_id = parsed.get("task_id") or source_file.stem
        body = parsed.get("body", "")
        msg_type = parsed.get("type", "review_request")
        verdict = parsed.get("verdict", "")

        if not reviewers:
            log(f"WARN review_request {source_file.name}: routing.review_requests_to is empty — falling back to generic delivery")
            return False

        content = compose_message(config, sender, reviewers, msg_type, task_id, body, verdict)
        delivered_to: list[str] = []

        for reviewer in reviewers:
            if require_ready and reviewer != escalation_target:
                ready = dispatch_dir / reviewer / "ready"
                if not ready.exists():
                    log(f"DEFER review_request {source_file.name}: {reviewer} not ready")
                    continue
            ensure_dispatch_dirs(dispatch_dir, reviewer)
            target = dispatch_dir / reviewer / "inbox" / compute_message_name(f"review-{sender}", task_id, config)
            write_message(target, content)
            queue_wake(reviewer, content)
            log(f"REVIEW-FAN-OUT {source_file.name}: {sender} -> {reviewer} ({msg_type})")
            monitor_buffer.append(f"review_request fan-out {sender} -> {reviewer} task={task_id}")
            delivered_to.append(reviewer)

        for cc in cc_targets:
            if cc in reviewers or cc == sender:
                continue
            if require_ready and cc != escalation_target:
                ready = dispatch_dir / cc / "ready"
                if not ready.exists():
                    continue
            ensure_dispatch_dirs(dispatch_dir, cc)
            cc_content = compose_message(config, sender, [cc], msg_type, task_id, body, verdict)
            cc_file = dispatch_dir / cc / "inbox" / compute_message_name(f"review-cc-{sender}", task_id, config)
            write_message(cc_file, cc_content)
            queue_wake(cc, cc_content)
            log(f"REVIEW-CC {source_file.name}: {sender} -> {cc} ({msg_type})")

        # Use "review" key (config schema defines fan_in.review, not fan_in.review_request)
        fan_in_cfg = config.get("fan_in", {}).get("review")
        if fan_in_cfg and delivered_to:
            trackers[task_id] = FanInTracker(
                request_id=task_id,
                msg_type=msg_type,
                sender=sender,
                required=list(fan_in_cfg.get("required", delivered_to)),
                timeout_seconds=int(fan_in_cfg.get("timeout_seconds", 300)),
                on_timeout=str(fan_in_cfg.get("on_timeout", "escalate_allan")),
                original_body=body,
            )
            save_trackers(tracker_path, trackers)
            log(f"FAN-IN START {task_id}: waiting for {trackers[task_id].required}")

        audit_log(
            "review_request_fan_out",
            project_root=project_root,
            config=config,
            sender=sender,
            task_id=task_id,
            reviewers=delivered_to,
            cc=cc_targets,
            source_file=source_file.name,
        )
        return True

    log(f"Watcher started project={project_root} dispatch={dispatch_dir} wake_mechanism={wake_mechanism}")

    # Liveness ticker (F4) -- daemon thread
    ltu_dir = resolve_path("state_root", project_root, config) / "last_tool_use"
    ltu_dir.mkdir(parents=True, exist_ok=True)
    liveness_thread = threading.Thread(
        target=liveness_ticker_thread,
        args=(agent_names, dispatch_dir, ltu_dir, wake_cfg, stop_file,
              wake_mechanism, session_prefix, project_root, config, log),
        daemon=True,
        name="liveness-ticker",
    )
    liveness_thread.start()
    log("Liveness ticker started")

    try:
        while not stop_file.exists():
            # process outbox
            for outbox_file in sort_files_by_mtime(dispatch_dir.glob("*/outbox/*")):
                if not outbox_file.is_file() or outbox_file.stat().st_size == 0:
                    continue
                sender = outbox_file.parent.parent.name
                try:
                    content = outbox_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                parsed = parse_message(content)
                parsed["from"] = parsed.get("from") or sender
                if parsed.get("type") == "review_request":
                    handle_review_request(parsed["from"], parsed, outbox_file)
                else:
                    deliver_message(parsed["from"], parsed, outbox_file)
                move_file(outbox_file, dispatch_dir / sender / "archive")

            # process reports
            for report_file in sort_files_by_mtime(dispatch_dir.glob("*/reports/*")):
                if not report_file.is_file() or report_file.stat().st_size == 0:
                    continue
                reporter = report_file.parent.parent.name
                try:
                    content = report_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                parsed = parse_message(content)
                parsed["from"] = parsed.get("from") or reporter
                request_id = parsed.get("task_id") or report_file.stem
                tracker = trackers.get(request_id)
                if tracker and reporter in tracker.required:
                    tracker.received[reporter] = content.strip()
                    save_trackers(tracker_path, trackers)
                    log(f"FAN-IN RESPONSE {request_id}: {reporter} ({len(tracker.missing())} remaining)")
                    monitor_buffer.append(f"fan-in response {reporter} for {request_id}")
                    move_file(report_file, dispatch_dir / reporter / "done")
                else:
                    direct_targets = parsed.get("to", [])
                    if direct_targets:
                        deliver_message(parsed["from"], parsed, report_file, direct_to=direct_targets)
                        move_file(report_file, dispatch_dir / reporter / "done")
                    else:
                        log(f"WARN unmatched report left in place: {report_file.name}")

            # complete / timeout fan-ins
            for request_id, tracker in list(trackers.items()):
                if tracker.is_complete():
                    merged_lines = [f"MERGED REVIEW FEEDBACK -- {request_id}", ""]
                    for agent in sorted(tracker.received):
                        merged_lines.append(f"--- {agent.upper()} ---")
                        merged_lines.append(tracker.received[agent].strip())
                        merged_lines.append("")
                    merged_body = "\n".join(merged_lines).strip()
                    sender_target = dispatch_dir / tracker.sender / "inbox" / compute_message_name("merged", request_id, config)
                    write_message(sender_target, compose_message(config, "watcher", [tracker.sender], "fan_in_complete", request_id, merged_body))
                    queue_wake(tracker.sender, merged_body)
                    for cc in config.get("routing", {}).get("cc_all", []):
                        if cc != tracker.sender:
                            cc_file = dispatch_dir / cc / "inbox" / compute_message_name("fanin", request_id, config)
                            write_message(cc_file, compose_message(config, "watcher", [cc], "fan_in_complete", request_id, f"Fan-in complete for {request_id}."))
                            queue_wake(cc, f"Fan-in complete for {request_id}.")
                    log(f"FAN-IN COMPLETE {request_id} -> {tracker.sender}")
                    # D2: apply consensus rule, write merged_verdicts/<task_id>.json
                    # trackers.pop() is inside the try — tracker preserved if verdict write fails
                    # Guard: skip verdict if no reviewers required (misconfiguration)
                    if not tracker.required:
                        log(f"WARN {request_id}: zero required reviewers — verdict skipped, tracker preserved")
                        continue
                    # approve_words: canonical verdict accept strings for this codebase
                    consensus_rule = config.get("gate", {}).get("consensus_rule", "unanimous")
                    approve_words = {"approved", "approve", "pass", "passed"}
                    verdicts: dict = {}
                    for reviewer in tracker.required:
                        content = tracker.received.get(reviewer, "")
                        parsed_v = parse_message(content) if content else {}
                        v = parsed_v.get("verdict", "").lower()
                        if not v:
                            log(f"WARN {request_id}: reviewer {reviewer} has no VERDICT header — treated as rejected")
                        verdicts[reviewer] = v

                    approve_count = sum(1 for v in verdicts.values() if v in approve_words)
                    total = len(tracker.required)

                    if consensus_rule == "majority":
                        # Strict majority: tie (e.g. 1/2) goes to rejected
                        overall = "approved" if approve_count > total / 2 else "rejected"
                    elif consensus_rule == "any_pass":
                        overall = "approved" if approve_count >= 1 else "rejected"
                    else:  # unanimous (default)
                        overall = "approved" if approve_count == total else "rejected"

                    dissent = [r for r in tracker.required if verdicts.get(r, "") not in approve_words]

                    try:
                        merged_verdicts_dir = resolve_path("merged_verdicts", project_root, config)
                        merged_verdicts_dir.mkdir(parents=True, exist_ok=True)
                        write_json(merged_verdicts_dir / f"{request_id}.json", {
                            "task_id": request_id,
                            "verdict": overall,
                            "consensus_rule": consensus_rule,
                            "verdicts": verdicts,
                            "dissent": dissent,
                            "ts": timestamp(config),
                        })
                        audit_log("fan_in_verdict", project_root=project_root, config=config,
                                  task_id=request_id, verdict=overall,
                                  consensus_rule=consensus_rule, dissent=dissent)
                        log(f"VERDICT {request_id}: {overall} ({consensus_rule}) dissent={dissent}")
                        # Only pop after successful write — tracker preserved if write fails
                        trackers.pop(request_id, None)
                        save_trackers(tracker_path, trackers)
                    except Exception as exc:
                        log(f"ERROR writing merged verdict {request_id} — tracker preserved for recovery: {exc}")
                    continue

                if tracker.is_timed_out() and not tracker.escalated:
                    body = (
                        f"ESCALATION: {request_id} timed out.\n"
                        f"Missing: {', '.join(tracker.missing()) or 'none'}\n"
                        f"Received: {', '.join(sorted(tracker.received)) or 'none'}\n"
                    )
                    if escalation_target:
                        allan_file = dispatch_dir / escalation_target / "inbox" / compute_message_name("escalation", request_id, config)
                        write_message(allan_file, compose_message(config, "watcher", [escalation_target], "escalation", request_id, body))
                        queue_wake(escalation_target, body)
                    else:
                        log(f"WARNING: escalation_target is empty — cannot notify for timeout of {request_id}")
                    tracker.escalated = True
                    save_trackers(tracker_path, trackers)
                    log(f"TIMEOUT {request_id}: escalated to {escalation_target}")
                    for cc in config.get("routing", {}).get("cc_all", []):
                        cc_file = dispatch_dir / cc / "inbox" / compute_message_name("escalation", request_id, config)
                        write_message(cc_file, compose_message(config, "watcher", [cc], "escalation", request_id, body))
                        queue_wake(cc, body)

            # wakes
            now = time.time()
            for agent, wake in list(pending_wakes.items()):
                inbox_dir = dispatch_dir / agent / "inbox"
                has_unread = any(p for p in inbox_dir.iterdir() if p.is_file() and p.suffix != ".tmp") if inbox_dir.is_dir() else False
                if not has_unread:
                    pending_wakes.pop(agent, None)
                    continue
                if not wake["first_sent"] and (now - wake["delivered_at"]) >= first_attempt_seconds:
                    wake_agent(agent, wake_mechanism, session_prefix)
                    wake["first_sent"] = True
                    wake["last_retry_at"] = now
                    continue
                if wake["first_sent"] and wake["retries"] < max_retries and (now - wake["last_retry_at"]) >= retry_interval_seconds:
                    wake["retries"] += 1
                    wake["last_retry_at"] = now
                    wake_agent(agent, wake_mechanism, session_prefix)

            if monitor_buffer and (time.time() - last_pulse) >= pulse_interval_seconds:
                pulse_body = "\n".join(monitor_buffer)
                for cc in config.get("routing", {}).get("cc_all", []):
                    pulse_file = dispatch_dir / cc / "inbox" / compute_message_name("pulse", "watcher", config)
                    write_message(pulse_file, compose_message(config, "watcher", [cc], "pulse", "", pulse_body))
                    queue_wake(cc, pulse_body)
                monitor_buffer.clear()
                last_pulse = time.time()

            time.sleep(1)
    except Exception:
        import traceback as _traceback
        tb = _traceback.format_exc()
        try:
            audit_log("watcher_crash", project_root=project_root, config=config,
                      traceback=tb)
        except Exception:
            pass
        try:
            crash_body = f"Watcher crashed:\n\n{tb}"
            for cc in config.get("routing", {}).get("cc_all", []):
                crash_file = (
                    dispatch_dir / cc / "inbox"
                    / compute_message_name("crash", "watcher", config)
                )
                write_message(
                    crash_file,
                    compose_message(config, "watcher", [cc], "crash_report", "", crash_body),
                )
        except Exception:
            pass
        try:
            log(f"CRASH: {tb}")
        except Exception:
            pass
        return 1

    log("STOP detected. Watcher exiting.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
