r"""Activity Sensing Gym (THUNLP ProactiveAgent Event Tracker)
===========================================================
Tracks user session events, code modifications, system activity logs, and
memory states to provide environment context for proactive goal prediction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class UserEvent:
    """Immutable environment activity event."""

    event_type: str  # "code_edit", "command_run", "test_pass", "oom_warning"
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ActivitySensingGym:
    """Environment activity tracker for proactive agent decision-making."""

    def __init__(self, max_history: int = 100) -> None:
        self.max_history = max_history
        self._history: list[UserEvent] = []

    def log_event(self, event_type: str, payload: dict[str, Any] | None = None) -> UserEvent:
        """Log a new activity event to the gym environment."""
        event = UserEvent(event_type=event_type, payload=payload or {})
        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history.pop(0)
        return event

    def get_recent_events(self, count: int = 10) -> list[UserEvent]:
        """Retrieve recent environment events."""
        return self._history[-count:]

    def clear(self) -> None:
        """Clear activity history."""
        self._history.clear()
