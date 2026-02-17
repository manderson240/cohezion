"""Compound metrics collector — singleton tracking compound loop health."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from cohezion.concurrency.safe_singleton import safe_singleton


logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    """Record of a single compound execution."""

    skill_name: str
    success: bool
    tokens_used: int
    duration_ms: float
    model_used: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class RefinementRecord:
    """Record of a skill refinement."""

    skill_name: str
    version_before: str
    version_after: str
    learnings_added: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class CycleRecord:
    """Record of a full compound feedback cycle."""

    skill_name: str
    executions: int
    refinements: int
    compound_score_delta: float
    total_tokens: int
    total_duration_ms: float
    timestamp: float = field(default_factory=time.time)


class CompoundMetricsCollector:
    """Singleton collector for compound engineering metrics.

    Tracks executions, refinements, cycles, and provides aggregated
    health reporting. Use `get_collector()` to get the singleton.
    """

    def __init__(self) -> None:
        self._executions: list[ExecutionRecord] = []
        self._refinements: list[RefinementRecord] = []
        self._cycles: list[CycleRecord] = []
        self._lock = threading.Lock()

    def record_execution(
        self,
        skill_name: str,
        success: bool,
        tokens_used: int,
        duration_ms: float,
        model_used: str = "",
    ) -> None:
        """Record a compound execution."""
        with self._lock:
            self._executions.append(
                ExecutionRecord(
                    skill_name=skill_name,
                    success=success,
                    tokens_used=tokens_used,
                    duration_ms=duration_ms,
                    model_used=model_used,
                )
            )
        logger.debug("Recorded execution: %s (success=%s)", skill_name, success)

    def record_refinement(
        self,
        skill_name: str,
        version_before: str,
        version_after: str,
        learnings_added: int,
    ) -> None:
        """Record a skill refinement."""
        with self._lock:
            self._refinements.append(
                RefinementRecord(
                    skill_name=skill_name,
                    version_before=version_before,
                    version_after=version_after,
                    learnings_added=learnings_added,
                )
            )
        logger.debug(
            "Recorded refinement: %s %s->%s",
            skill_name,
            version_before,
            version_after,
        )

    def record_cycle(
        self,
        skill_name: str,
        executions: int,
        refinements: int,
        compound_score_delta: float,
        total_tokens: int,
        total_duration_ms: float,
    ) -> None:
        """Record a complete compound feedback cycle."""
        with self._lock:
            self._cycles.append(
                CycleRecord(
                    skill_name=skill_name,
                    executions=executions,
                    refinements=refinements,
                    compound_score_delta=compound_score_delta,
                    total_tokens=total_tokens,
                    total_duration_ms=total_duration_ms,
                )
            )
        logger.debug("Recorded cycle: %s (delta=%.4f)", skill_name, compound_score_delta)

    @property
    def total_executions(self) -> int:
        """Total number of recorded executions."""
        return len(self._executions)

    @property
    def total_refinements(self) -> int:
        """Total number of recorded refinements."""
        return len(self._refinements)

    @property
    def total_cycles(self) -> int:
        """Total number of recorded cycles."""
        return len(self._cycles)

    def success_rate(self) -> float:
        """Overall execution success rate."""
        if not self._executions:
            return 0.0
        successes = sum(1 for e in self._executions if e.success)
        return successes / len(self._executions)

    def total_tokens(self) -> int:
        """Total tokens consumed across all executions."""
        return sum(e.tokens_used for e in self._executions)

    def model_usage(self) -> dict[str, int]:
        """Count of executions per model."""
        usage: dict[str, int] = {}
        for e in self._executions:
            model = e.model_used or "unknown"
            usage[model] = usage.get(model, 0) + 1
        return usage

    def top_refined_skills(self, limit: int = 10) -> list[tuple[str, int]]:
        """Skills with most refinements."""
        counts: dict[str, int] = {}
        for r in self._refinements:
            counts[r.skill_name] = counts.get(r.skill_name, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    def compound_score_trend(self) -> list[dict[str, Any]]:
        """Compound score deltas over time."""
        return [
            {
                "skill_name": c.skill_name,
                "compound_score_delta": c.compound_score_delta,
                "timestamp": c.timestamp,
            }
            for c in self._cycles
        ]

    def skill_history(self, skill_name: str) -> dict[str, Any]:
        """Get execution and refinement history for a specific skill."""
        execs = [e for e in self._executions if e.skill_name == skill_name]
        refs = [r for r in self._refinements if r.skill_name == skill_name]
        cycles = [c for c in self._cycles if c.skill_name == skill_name]
        return {
            "skill_name": skill_name,
            "executions": len(execs),
            "refinements": len(refs),
            "cycles": len(cycles),
            "total_tokens": sum(e.tokens_used for e in execs),
            "success_rate": (sum(1 for e in execs if e.success) / len(execs) if execs else 0.0),
            "latest_execution": execs[-1].timestamp if execs else None,
            "latest_refinement": refs[-1].timestamp if refs else None,
        }

    def to_health_dict(self) -> dict[str, Any]:
        """Return full health report as a dict."""
        return {
            "total_executions": self.total_executions,
            "total_refinements": self.total_refinements,
            "total_cycles": self.total_cycles,
            "success_rate": round(self.success_rate(), 4),
            "total_tokens": self.total_tokens(),
            "model_usage": self.model_usage(),
            "top_refined_skills": [{"skill": name, "count": count} for name, count in self.top_refined_skills()],
            "compound_score_trend": self.compound_score_trend(),
        }

    def to_snapshot(self) -> dict[str, Any]:
        """Serialize collector state for persistence."""
        return {
            "executions": [
                {
                    "skill_name": e.skill_name,
                    "success": e.success,
                    "tokens_used": e.tokens_used,
                    "duration_ms": e.duration_ms,
                    "model_used": e.model_used,
                    "timestamp": e.timestamp,
                }
                for e in self._executions
            ],
            "refinements": [
                {
                    "skill_name": r.skill_name,
                    "version_before": r.version_before,
                    "version_after": r.version_after,
                    "learnings_added": r.learnings_added,
                    "timestamp": r.timestamp,
                }
                for r in self._refinements
            ],
            "cycles": [
                {
                    "skill_name": c.skill_name,
                    "executions": c.executions,
                    "refinements": c.refinements,
                    "compound_score_delta": c.compound_score_delta,
                    "total_tokens": c.total_tokens,
                    "total_duration_ms": c.total_duration_ms,
                    "timestamp": c.timestamp,
                }
                for c in self._cycles
            ],
        }

    def load_from_snapshot(self, data: dict[str, Any]) -> None:
        """Restore collector state from a snapshot."""
        self._executions = [ExecutionRecord(**e) for e in data.get("executions", [])]
        self._refinements = [RefinementRecord(**r) for r in data.get("refinements", [])]
        self._cycles = [CycleRecord(**c) for c in data.get("cycles", [])]

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        self._executions.clear()
        self._refinements.clear()
        self._cycles.clear()


@safe_singleton
def get_collector() -> CompoundMetricsCollector:
    """Return the singleton CompoundMetricsCollector."""
    return CompoundMetricsCollector()


def reset_collector() -> None:
    """Reset the singleton (for testing)."""
    get_collector.reset()
