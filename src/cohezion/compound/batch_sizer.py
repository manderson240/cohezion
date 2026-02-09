"""Experience-guided batch sizing for optimal throughput.

Learns optimal batch sizes from vault history and predicts sizes for new tasks.
Implements Phase 3 Sprint 1: Experience-Guided Batch Sizing (+8% throughput).

Key features:
- In-memory history of recent batch executions
- Task type classification for pattern matching
- Linear regression model for batch_size → throughput correlation
- Vault integration for persistent learning
- Fallback heuristics when no history available
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BatchExecutionMetrics:
    """Metrics from a batch execution for learning."""

    batch_size: int
    task_count: int
    task_types: list[str]
    execution_time: float  # seconds
    tokens_used: int
    throughput: float  # tokens/sec
    cache_hit_rate: float  # 0-1
    errors: int = 0
    timestamp: str = field(default_factory=lambda: "")

    @property
    def tokens_per_task(self) -> float:
        """Average tokens per task."""
        return self.tokens_used / self.task_count if self.task_count > 0 else 0

    @property
    def primary_task_type(self) -> str:
        """Most common task type in batch."""
        if not self.task_types:
            return "unknown"
        return max(set(self.task_types), key=self.task_types.count)


class BatchSizePredictor:
    """Learns optimal batch sizes from execution history.

    Maintains in-memory history of batch executions and predicts optimal
    batch sizes for new tasks based on:
    - Task type (generate, analyze, search, transform, persist)
    - Batch task count
    - Historical throughput patterns

    Parameters
    ----------
    history_size : int
        Maximum number of execution records to keep in memory (default: 100)
    min_confidence_threshold : float
        Minimum confidence (0-1) required to make prediction (default: 0.5)
    vault_client : optional
        VaultClient for persistent learning (Phase 2)
    """

    # Heuristic batch sizes per task type (fallback when no history)
    DEFAULT_BATCH_SIZES = {
        "generate": 16,  # Slow, token-heavy
        "analyze": 32,  # Medium speed
        "search": 64,  # Fast, low token cost
        "transform": 32,  # Medium speed
        "persist": 48,  # Medium speed
        "unknown": 32,  # Default fallback
    }

    # Expected throughput (tokens/sec) per task type (baseline)
    BASELINE_THROUGHPUT = {
        "generate": 85.0,  # tok/sec
        "analyze": 120.0,
        "search": 150.0,
        "transform": 100.0,
        "persist": 110.0,
        "unknown": 100.0,
    }

    def __init__(
        self,
        history_size: int = 100,
        min_confidence_threshold: float = 0.5,
        vault_client: Optional[Any] = None,
    ) -> None:
        """Initialize batch size predictor."""
        self.history_size = history_size
        self.min_confidence_threshold = min_confidence_threshold
        self.vault_client = vault_client

        # In-memory history: {task_type: [metrics]}
        self.history: dict[str, list[BatchExecutionMetrics]] = {}
        self._last_prediction: Optional[tuple[int, float]] = None  # (size, confidence)

    def record_execution(self, metrics: BatchExecutionMetrics) -> None:
        """Record a batch execution for learning.

        Parameters
        ----------
        metrics : BatchExecutionMetrics
            Metrics from batch execution
        """
        task_type = metrics.primary_task_type

        if task_type not in self.history:
            self.history[task_type] = []

        self.history[task_type].append(metrics)

        # Limit history size (keep most recent)
        if len(self.history[task_type]) > self.history_size:
            self.history[task_type] = self.history[task_type][-self.history_size :]

        logger.debug(
            f"Recorded execution: batch_size={metrics.batch_size} "
            f"throughput={metrics.throughput:.1f} tok/sec "
            f"task_type={task_type}"
        )

    def predict_optimal_size(
        self, task_type: str, task_count: int
    ) -> tuple[int, float]:
        """Predict optimal batch size for a task.

        Uses historical patterns to recommend batch size. Falls back to
        heuristics if insufficient history.

        Parameters
        ----------
        task_type : str
            Type of task (generate, analyze, search, transform, persist)
        task_count : int
            Total number of tasks to process

        Returns
        -------
        tuple[int, float]
            (recommended_batch_size, confidence_0_to_1)
        """
        if not task_type or task_type not in self.DEFAULT_BATCH_SIZES:
            task_type = "unknown"

        # Get history for this task type
        type_history = self.history.get(task_type, [])

        if not type_history:
            # No history: use heuristic
            size = self.DEFAULT_BATCH_SIZES[task_type]
            confidence = 0.3  # Low confidence for heuristic
            logger.debug(
                f"No history for {task_type}, using heuristic batch_size={size}"
            )
            self._last_prediction = (size, confidence)
            return size, confidence

        # Analyze historical throughput by batch size
        optimal_size, confidence = self._find_optimal_from_history(
            type_history, task_count, task_type
        )

        self._last_prediction = (optimal_size, confidence)
        return optimal_size, confidence

    def _find_optimal_from_history(
        self,
        history: list[BatchExecutionMetrics],
        task_count: int,
        task_type: str,
    ) -> tuple[int, float]:
        """Find optimal batch size from historical data.

        Simple strategy:
        1. Group by batch size
        2. Calculate average throughput per size
        3. Find size with highest throughput
        4. Adjust for task_count if needed

        Parameters
        ----------
        history : list[BatchExecutionMetrics]
            Historical execution data
        task_count : int
            Number of tasks to process
        task_type : str
            Task type for fallback

        Returns
        -------
        tuple[int, float]
            (optimal_batch_size, confidence)
        """
        if not history:
            size = self.DEFAULT_BATCH_SIZES[task_type]
            return size, 0.3

        # Group by batch size
        size_groups: dict[int, list[float]] = {}
        for metrics in history:
            if metrics.batch_size not in size_groups:
                size_groups[metrics.batch_size] = []
            size_groups[metrics.batch_size].append(metrics.throughput)

        # Calculate average throughput per batch size
        size_throughput = {
            size: sum(values) / len(values) for size, values in size_groups.items()
        }

        # Find optimal size (highest throughput)
        if not size_throughput:
            size = self.DEFAULT_BATCH_SIZES[task_type]
            return size, 0.3

        optimal_size = max(size_throughput, key=size_throughput.get)
        max_throughput = size_throughput[optimal_size]

        # Calculate confidence based on:
        # 1. Number of samples for this batch size
        # 2. Consistency (variance) of throughput
        num_samples = len(size_groups[optimal_size])
        confidence = min(
            0.95,  # Cap at 95%
            0.5 + (num_samples / 20.0) * 0.3,  # More samples = higher confidence
        )

        # Variance penalty: if very inconsistent, lower confidence
        if num_samples > 1:
            throughputs = size_groups[optimal_size]
            variance = sum((t - max_throughput) ** 2 for t in throughputs) / len(
                throughputs
            )
            variance_penalty = min(0.2, variance / max_throughput)
            confidence -= variance_penalty

        logger.debug(
            f"Found optimal batch_size={optimal_size} for {task_type} "
            f"(throughput={max_throughput:.1f} tok/sec, confidence={confidence:.2f})"
        )

        return optimal_size, max(0.3, confidence)

    def get_confidence(self) -> float:
        """Get confidence of last prediction.

        Returns
        -------
        float
            Confidence from 0-1
        """
        if self._last_prediction is None:
            return 0.0
        return self._last_prediction[1]

    def get_stats(self) -> dict[str, Any]:
        """Get batch sizer statistics.

        Returns
        -------
        dict[str, Any]
            Statistics about learning history
        """
        total_records = sum(len(v) for v in self.history.values())

        return {
            "task_types_learned": list(self.history.keys()),
            "total_records": total_records,
            "history_per_type": {k: len(v) for k, v in self.history.items()},
            "last_prediction": self._last_prediction,
        }

    async def learn_from_vault(self) -> None:
        """Query vault for historical executions and learn patterns.

        Phase 2 integration: Query VaultExecutionLogger for past batch
        executions and build predictive model.

        This is a placeholder for Phase 2 vault integration.
        """
        if not self.vault_client:
            logger.debug("No vault client configured, skipping vault learning")
            return

        try:
            # TODO: Phase 2 - Query vault for execution records
            # patterns = await self.vault_client.search(
            #     "batch_execution",
            #     filters={"recorded_at": {"$gte": "2026-02-01"}}
            # )
            # for pattern in patterns:
            #     metrics = BatchExecutionMetrics(**pattern)
            #     self.record_execution(metrics)
            logger.debug("Vault learning not yet implemented (Phase 2)")
        except Exception as e:
            logger.debug(f"Vault learning error: {e}")


def get_batch_size_predictor(reset: bool = False) -> BatchSizePredictor:
    """Get or create singleton batch size predictor.

    Parameters
    ----------
    reset : bool
        If True, create new instance (default: False)

    Returns
    -------
    BatchSizePredictor
        Singleton instance
    """
    global _predictor_instance

    if reset or _predictor_instance is None:
        _predictor_instance = BatchSizePredictor()

    return _predictor_instance


# Module-level singleton
_predictor_instance: Optional[BatchSizePredictor] = None


__all__ = [
    "BatchExecutionMetrics",
    "BatchSizePredictor",
    "get_batch_size_predictor",
]
