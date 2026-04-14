#!/usr/bin/env python3
"""Routing rules for the consolidated monitor stream."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


@dataclass(frozen=True)
class MonitorRouteDecision:
    deliver: bool
    recipients: list[str]
    source_priority: str
    focus: str
    reason: str


class MonitorRouter:
    """Choose when parsed monitor events should reach monitor recipients."""

    def __init__(
        self,
        *,
        monitor_targets: Iterable[str],
        primary_agents: Iterable[str],
        reviewer_roles: Iterable[str] = ("reviewer",),
        idle_seconds: int = 120,
    ) -> None:
        self.monitor_targets = [target for target in monitor_targets if target]
        self.primary_agents = {agent for agent in primary_agents if agent}
        self.reviewer_roles = {role for role in reviewer_roles if role}
        self.idle_after = timedelta(seconds=max(idle_seconds, 0))
        self.last_primary_event_at: datetime | None = None

    def route_event(self, event: dict, *, now: datetime | None = None) -> MonitorRouteDecision:
        event_at = _parse_timestamp(event.get("timestamp")) or now or datetime.now(timezone.utc)
        source_priority = self._source_priority(event)
        if source_priority == "primary":
            self.last_primary_event_at = event_at
            return MonitorRouteDecision(
                deliver=True,
                recipients=list(self.monitor_targets),
                source_priority="primary",
                focus="primary",
                reason="primary_source",
            )

        primary_idle = self._is_primary_idle(now or event_at)
        carries_secondary_signal = bool(event.get("decision_messages") or event.get("warning_messages"))
        deliver = primary_idle or carries_secondary_signal
        reason = "primary_idle" if primary_idle else "secondary_signal" if carries_secondary_signal else "primary_active"
        focus = "secondary" if primary_idle else "primary"
        recipients = list(self.monitor_targets) if deliver else []
        return MonitorRouteDecision(
            deliver=deliver,
            recipients=recipients,
            source_priority="secondary",
            focus=focus,
            reason=reason,
        )

    def _source_priority(self, event: dict) -> str:
        source_agent = str(event.get("source_agent") or "").strip()
        source_role = str(event.get("source_role") or "").strip()
        if source_agent in self.primary_agents:
            return "primary"
        if source_role in self.reviewer_roles:
            return "secondary"
        return "secondary"

    def _is_primary_idle(self, now: datetime) -> bool:
        if self.last_primary_event_at is None:
            return True
        return now - self.last_primary_event_at >= self.idle_after
