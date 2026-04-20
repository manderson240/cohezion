"""Unified metrics collector.

Replaces metrics.py (276 lines) + global_metrics_aggregator.py (640 lines) +
thermodynamic_metrics.py (565 lines) with single unified system.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.models import ExecutionResult


logger = logging.getLogger(__name__)


@dataclass
class MetricsSnapshot:
    """Snapshot of current metrics."""

    timestamp: float = field(default_factory=time.time)

    # Execution metrics
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0

    # Performance metrics
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0

    # Token metrics
    total_tokens: int = 0
    avg_tokens_per_execution: float = 0.0

    # Quality metrics
    avg_coherence: float = 0.0
    avg_quality_score: float = 0.0


class MetricsCollector:
    """Unified metrics collection.

    Replaces:
    - metrics.py (276 lines)
    - global_metrics_aggregator.py (640 lines)
    - thermodynamic_metrics.py (565 lines)

    Total: 1,481 lines → ~150 lines
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.results: deque[ExecutionResult] = deque(maxlen=window_size)
        self._total_tokens = 0
        self._total_duration = 0.0

    def record(self, result: ExecutionResult) -> None:
        """Record execution result."""
        self.results.append(result)
        self._total_tokens += result.metrics.total_tokens
        self._total_duration += result.metrics.duration_seconds

    def get_snapshot(self) -> MetricsSnapshot:
        """Get current metrics snapshot."""
        if not self.results:
            return MetricsSnapshot()

        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful

        durations = [r.metrics.duration_seconds * 1000 for r in self.results]
        avg_duration = sum(durations) / len(durations)

        # Calculate P95
        sorted_durations = sorted(durations)
        p95_idx = int(len(sorted_durations) * 0.95)
        p95_duration = sorted_durations[min(p95_idx, len(sorted_durations) - 1)]

        coherences = [r.metrics.coherence for r in self.results if r.metrics.coherence > 0]
        avg_coherence = sum(coherences) / len(coherences) if coherences else 0.0

        qualities = [
            r.metrics.quality_score for r in self.results if r.metrics.quality_score is not None
        ]
        avg_quality = sum(qualities) / len(qualities) if qualities else 0.0

        return MetricsSnapshot(
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            avg_duration_ms=avg_duration,
            p95_duration_ms=p95_duration,
            total_tokens=self._total_tokens,
            avg_tokens_per_execution=self._total_tokens / total if total > 0 else 0,
            avg_coherence=avg_coherence,
            avg_quality_score=avg_quality,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get statistics as dictionary."""
        snapshot = self.get_snapshot()
        return {
            "executions": {
                "total": snapshot.total_executions,
                "successful": snapshot.successful_executions,
                "failed": snapshot.failed_executions,
                "success_rate": (
                    snapshot.successful_executions / snapshot.total_executions
                    if snapshot.total_executions > 0
                    else 0.0
                ),
            },
            "performance": {
                "avg_duration_ms": snapshot.avg_duration_ms,
                "p95_duration_ms": snapshot.p95_duration_ms,
            },
            "tokens": {
                "total": snapshot.total_tokens,
                "avg_per_execution": snapshot.avg_tokens_per_execution,
            },
            "quality": {
                "avg_coherence": snapshot.avg_coherence,
                "avg_quality_score": snapshot.avg_quality_score,
            },
        }

    def clear(self) -> None:
        """Clear all metrics."""
        self.results.clear()
        self._total_tokens = 0
        self._total_duration = 0.0

    def export(self) -> list[dict[str, Any]]:
        """Export all results for persistence."""
        return [r.to_dict() for r in self.results]


class SimpleMetrics:
    """Minimal metrics for basic use cases."""

    def __init__(self):
        self.execution_count = 0
        self.total_duration = 0.0
        self.total_tokens = 0

    def record(self, result: ExecutionResult) -> None:
        self.execution_count += 1
        self.total_duration += result.metrics.duration_seconds
        self.total_tokens += result.metrics.total_tokens

    @property
    def avg_duration(self) -> float:
        return self.total_duration / self.execution_count if self.execution_count > 0 else 0.0

    @property
    def avg_tokens(self) -> float:
        return self.total_tokens / self.execution_count if self.execution_count > 0 else 0.0
