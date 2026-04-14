from datetime import datetime, timedelta, timezone

from scripts.monitor_route import MonitorRouter


BASE_TIME = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)


def _event(
    *,
    source_agent: str,
    source_role: str,
    timestamp: datetime,
    decision_messages=None,
    warning_messages=None,
):
    return {
        "session_id": "session-1",
        "source_agent": source_agent,
        "source_role": source_role,
        "source_kind": "session_jsonl",
        "timestamp": timestamp.isoformat(),
        "record_type": "assistant",
        "uuid": f"{source_agent}-{int(timestamp.timestamp())}",
        "monitor_text": f"{source_agent} says hello",
        "decision_messages": decision_messages or [],
        "warning_messages": warning_messages or [],
    }


def test_ralph_live_stream_is_primary_source():
    router = MonitorRouter(
        monitor_targets=["gate-monitor"],
        primary_agents={"gate-ralph"},
        idle_seconds=120,
    )

    decision = router.route_event(
        _event(source_agent="gate-ralph", source_role="coder", timestamp=BASE_TIME),
        now=BASE_TIME,
    )

    assert decision.deliver is True
    assert decision.source_priority == "primary"
    assert decision.focus == "primary"
    assert decision.recipients == ["gate-monitor"]


def test_reviewer_updates_are_secondary_while_ralph_is_active():
    router = MonitorRouter(
        monitor_targets=["gate-monitor"],
        primary_agents={"gate-ralph"},
        idle_seconds=120,
    )
    router.route_event(
        _event(source_agent="gate-ralph", source_role="coder", timestamp=BASE_TIME),
        now=BASE_TIME,
    )

    decision = router.route_event(
        _event(
            source_agent="gate-critic",
            source_role="reviewer",
            timestamp=BASE_TIME + timedelta(seconds=10),
        ),
        now=BASE_TIME + timedelta(seconds=10),
    )

    assert decision.deliver is False
    assert decision.source_priority == "secondary"
    assert decision.focus == "primary"
    assert decision.recipients == []


def test_reviewer_updates_shift_focus_when_ralph_is_idle():
    router = MonitorRouter(
        monitor_targets=["gate-monitor"],
        primary_agents={"gate-ralph"},
        idle_seconds=60,
    )
    router.route_event(
        _event(source_agent="gate-ralph", source_role="coder", timestamp=BASE_TIME),
        now=BASE_TIME,
    )

    decision = router.route_event(
        _event(
            source_agent="gate-architect",
            source_role="reviewer",
            timestamp=BASE_TIME + timedelta(seconds=90),
            decision_messages=["Spec mismatch on current batch"],
        ),
        now=BASE_TIME + timedelta(seconds=90),
    )

    assert decision.deliver is True
    assert decision.source_priority == "secondary"
    assert decision.focus == "secondary"
    assert decision.reason == "primary_idle"
    assert decision.recipients == ["gate-monitor"]


def test_routing_supports_fan_out_targets():
    router = MonitorRouter(
        monitor_targets=["gate-monitor", "gate-monitor-backup"],
        primary_agents={"gate-ralph"},
        idle_seconds=120,
    )

    decision = router.route_event(
        _event(
            source_agent="gate-critic",
            source_role="reviewer",
            timestamp=BASE_TIME,
            warning_messages=["Reviewer escalation"],
        ),
        now=BASE_TIME,
    )

    assert decision.deliver is True
    assert decision.recipients == ["gate-monitor", "gate-monitor-backup"]
