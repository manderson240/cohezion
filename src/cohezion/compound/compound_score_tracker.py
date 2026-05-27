"""Compound score tracker for monitoring ExecutionResult.compound_score over time.

The compound_score (0.6*coherence + 0.3*success + 0.1*efficiency) is computed
by execute_task() and stored in result.metrics["compound_score"]. This module
provides trend analysis over a window of results.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompoundScoreWindow:
    """Rolling window of compound scores with trend analysis."""

    window_size: int = 20
    _scores: deque = field(default_factory=lambda: deque(maxlen=20))

    def __post_init__(self):
        self._scores = deque(maxlen=self.window_size)

    def record(self, score: float) -> None:
        """Record a new compound score."""
        self._scores.append(float(score))

    @property
    def mean(self) -> float:
        if not self._scores:
            return 0.5
        return sum(self._scores) / len(self._scores)

    @property
    def trend(self) -> float:
        """Trend: positive = improving, negative = degrading, 0 = stable."""
        if len(self._scores) < 4:
            return 0.0
        first_half = list(self._scores)[: len(self._scores) // 2]
        second_half = list(self._scores)[len(self._scores) // 2 :]
        first_mean = sum(first_half) / len(first_half)
        second_mean = sum(second_half) / len(second_half)
        return round(second_mean - first_mean, 4)

    @property
    def is_improving(self) -> bool:
        return self.trend > 0.01

    @property
    def is_degrading(self) -> bool:
        return self.trend < -0.01

    def summary(self) -> dict[str, Any]:
        return {
            "n": len(self._scores),
            "mean": round(self.mean, 4),
            "trend": self.trend,
            "improving": self.is_improving,
            "degrading": self.is_degrading,
            "window_size": self.window_size,
        }
