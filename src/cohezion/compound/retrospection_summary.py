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


@dataclass
class StrategyTracker:
    """Tracks consecutive failures and improvement plateaus per skill.

    Used by CycleRetrospectionEngine to detect when an approach should be
    abandoned in favor of a fundamentally different strategy.
    """

    pivot_threshold: int = 3
    improvement_threshold: float = 0.05  # 5%
    _failure_counts: dict[str, int] = field(default_factory=dict)
    _improvement_history: dict[str, list[float]] = field(default_factory=dict)

    def record_outcome(self, skill_name: str, success: bool, metric_delta: float) -> str | None:
        """Record outcome. Returns pivot recommendation if threshold hit."""
        if not success:
            self._failure_counts[skill_name] = self._failure_counts.get(skill_name, 0) + 1
        else:
            self._failure_counts[skill_name] = 0

        history = self._improvement_history.setdefault(skill_name, [])
        history.append(metric_delta)

        # Check plateau: N attempts with <threshold improvement
        if len(history) >= self.pivot_threshold:
            recent = history[-self.pivot_threshold :]
            if all(abs(d) < self.improvement_threshold for d in recent):
                return (
                    f"PIVOT RECOMMENDED: {skill_name} has plateaued "
                    f"({self.pivot_threshold} attempts, "
                    f"<{self.improvement_threshold:.0%} improvement each)"
                )

        # Check consecutive failures
        count = self._failure_counts.get(skill_name, 0)
        if count >= self.pivot_threshold:
            return f"PIVOT RECOMMENDED: {skill_name} has failed {count} consecutive times"

        return None

    def reset(self, skill_name: str) -> None:
        """Reset tracking for a skill after a successful pivot."""
        self._failure_counts.pop(skill_name, None)
        self._improvement_history.pop(skill_name, None)


class CycleRetrospectionEngine:
    """Generates per-cycle retrospection summaries after compound cycles.

    The narrative uses first-person voice to maintain the singular
    Voice Identity across all system communications.

    Renamed from RetrospectionEngine 2026-04-22 (Sprint A) to disambiguate
    from the two other same-named classes that do different things:
      * core.compound.retrospection.RetrospectionEngine — parses
        KEY_LEARNINGS.md / MISSION_JOURNAL.md from the knowledge graph.
      * compound.autoresearch.VaultLearningCapture (was RetrospectionEngine)
        — captures learnings to vault via MCP.
    This class generates a CycleMetrics → RetrospectionSummary transformation
    per compound cycle. Backward-compat alias `RetrospectionEngine` at module
    bottom.
    """

    def __init__(self) -> None:
        self._summaries: list[RetrospectionSummary] = []
        self._strategy_tracker = StrategyTracker()

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

        # Check for strategy pivot recommendation
        pivot = self._strategy_tracker.record_outcome(metrics.skill_name, metrics.success, coherence_delta)
        if pivot:
            insights.append(pivot)
            logger.warning("Strategy pivot recommended for %s", metrics.skill_name)

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
            parts.append(f"I detected {len(metrics.anomalies)} anomalies that warrant further investigation.")

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


# Backward-compat alias — deprecated. Prefer CycleRetrospectionEngine, which
# disambiguates this per-cycle summary generator from
# core.compound.retrospection.RetrospectionEngine (KG parser). See
# patterns/deferred-sprints-consolidation-and-skills-migration.md.
RetrospectionEngine = CycleRetrospectionEngine
