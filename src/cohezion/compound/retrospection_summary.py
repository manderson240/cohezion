"""Retrospection Summaries (Story 5.4, FR18, NFR-4).

Generates structured first-person post-mortem summaries after each
compound cycle. Uses the singular Voice Identity for consistent
narrative across all agents.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class CycleMetrics:
    """Metrics from a completed compound cycle."""

    coherence_start: float
    coherence_end: float
    tokens_used: int
    skill_name: str
    phase: str  # "reflecting" | "refining" | "executing"
    success: bool
    anomalies: list[str] = field(default_factory=list)


@dataclass
class RetrospectionSummary:
    """A first-person post-mortem summary of a compound cycle."""

    cycle_id: str
    narrative: str  # First-person voice identity text
    metrics: CycleMetrics
    insights: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "narrative": self.narrative,
            "coherence_delta": self.metrics.coherence_end - self.metrics.coherence_start,
            "tokens_used": self.metrics.tokens_used,
            "skill_name": self.metrics.skill_name,
            "success": self.metrics.success,
            "insights": self.insights,
            "anomalies": self.metrics.anomalies,
            "timestamp": self.timestamp,
        }


class RetrospectionEngine:
    """Generates retrospection summaries after compound cycles.

    The narrative uses first-person voice to maintain the singular
    Voice Identity across all system communications.
    """

    def __init__(self) -> None:
        self._summaries: list[RetrospectionSummary] = []

    @property
    def summaries(self) -> list[RetrospectionSummary]:
        return list(self._summaries)

    def summarize(self, cycle_id: str, metrics: CycleMetrics) -> RetrospectionSummary:
        """Generate a retrospection summary for a completed cycle."""
        coherence_delta = metrics.coherence_end - metrics.coherence_start
        direction = "improved" if coherence_delta > 0 else "degraded"

        # Generate first-person narrative
        narrative = self._generate_narrative(metrics, coherence_delta, direction)
        insights = self._extract_insights(metrics, coherence_delta)

        summary = RetrospectionSummary(
            cycle_id=cycle_id,
            narrative=narrative,
            metrics=metrics,
            insights=insights,
        )
        self._summaries.append(summary)
        logger.info("Retrospection summary generated for cycle %s", cycle_id)
        return summary

    def _generate_narrative(
        self,
        metrics: CycleMetrics,
        delta: float,
        direction: str,
    ) -> str:
        """Generate first-person narrative in the singular Voice Identity."""
        status = "succeeded" if metrics.success else "encountered challenges"

        parts = [
            f"I {status} during the {metrics.phase} phase",
            f"while refining {metrics.skill_name}.",
            f"Coherence {direction} by {abs(delta):.3f}",
            f"(from {metrics.coherence_start:.3f} to {metrics.coherence_end:.3f}).",
            f"This cycle consumed {metrics.tokens_used} tokens.",
        ]

        if metrics.anomalies:
            parts.append(
                f"I detected {len(metrics.anomalies)} anomalies that warrant further investigation."
            )

        return " ".join(parts)

    def _extract_insights(self, metrics: CycleMetrics, delta: float) -> list[str]:
        """Extract actionable insights from cycle metrics."""
        insights: list[str] = []

        if delta < -0.1:
            insights.append("Significant coherence degradation — consider rollback")
        if delta > 0.1:
            insights.append("Strong coherence improvement — skill refinement effective")
        if metrics.tokens_used > 5000:
            insights.append("High token usage — consider decomposing task")
        if not metrics.success:
            insights.append("Cycle failed — freeze-frame captured for Ouroboros")
        if metrics.anomalies:
            insights.append(f"Anomalies detected: {', '.join(metrics.anomalies)}")

        return insights

    def get_recent(self, n: int = 5) -> list[dict]:
        """Get the N most recent summaries."""
        return [s.to_dict() for s in self._summaries[-n:]]
