"""Cross-session model usage tracking for tier optimization."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModelUsageEvent:
    """A single recorded model usage within a session."""

    session_id: str
    model_name: str
    started_at: float
    duration_s: float = 0.0
    task_type: str = "inference"  # "inference" | "training"


@dataclass
class SessionRecord:
    """Accumulated usage data for one Cohezion session."""

    session_id: str
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    model_events: list[ModelUsageEvent] = field(default_factory=list)

    def add_usage(
        self,
        model: str,
        duration_s: float,
        task_type: str = "inference",
    ) -> None:
        """Append a model usage event to this session record."""
        self.model_events.append(
            ModelUsageEvent(
                session_id=self.session_id,
                model_name=model,
                started_at=time.time(),
                duration_s=duration_s,
                task_type=task_type,
            )
        )

    def total_duration_s(self) -> float:
        """Return the sum of all model usage durations in this session."""
        return sum(ev.duration_s for ev in self.model_events)


class SessionTracker:
    """Track model usage across sessions.

    In-memory store used during the session; callers may also persist records
    to SurrealDB by passing a SurrealDBClient to persist_session().
    """

    def __init__(self) -> None:
        self._records: list[SessionRecord] = []

    def record_session(self, record: SessionRecord) -> None:
        """Add or replace a session record."""
        self._records = [r for r in self._records if r.session_id != record.session_id]
        self._records.append(record)
        logger.debug("Recorded session %s (%d events)", record.session_id, len(record.model_events))

    def get_usage_histogram(self, days: int = 7) -> dict[str, float]:
        """Return model_name -> total_usage_hours over the last N days.

        Filters events by started_at within the rolling window.
        """
        cutoff = time.time() - days * 86400
        totals: dict[str, float] = {}
        for record in self._records:
            for ev in record.model_events:
                if ev.started_at >= cutoff:
                    totals[ev.model_name] = totals.get(ev.model_name, 0.0) + ev.duration_s / 3600.0
        return totals

    def get_recent_sessions(self, limit: int = 100) -> list[SessionRecord]:
        """Return the most recently started sessions, newest first."""
        sorted_records = sorted(self._records, key=lambda r: r.started_at, reverse=True)
        return sorted_records[:limit]

    def session_model_usage(self, days: int = 7) -> dict[str, set[str]]:
        """Return model_name -> set of session_ids that used the model in last N days.

        Used by TierOptimizer to compute per-model session penetration.
        """
        cutoff = time.time() - days * 86400
        usage: dict[str, set[str]] = {}
        for record in self._records:
            for ev in record.model_events:
                if ev.started_at >= cutoff:
                    usage.setdefault(ev.model_name, set()).add(record.session_id)
        return usage
