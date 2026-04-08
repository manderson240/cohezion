"""Base Repository - Shared functionality for all repositories.

Implements compound engineering patterns:
- Batch operations for throughput
- Token-efficient context separation
- Built-in error handling and metrics
- Adversarial review integration points
"""

from __future__ import annotations

import logging
import time
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

import structlog


logger = structlog.get_logger(__name__)

# Type variables for generic repository pattern
T = TypeVar("T")
TFilter = TypeVar("TFilter")


@dataclass
class RepositoryMetrics:
    """Metrics for repository operations."""

    operation: str
    duration_ms: float
    success: bool
    items_processed: int = 1
    cache_hit: bool = False
    batch_size: int = 1
    error_message: str | None = None
    timestamp: str = field(default_factory=lambda: "")

    @classmethod
    def from_operation(
        cls,
        operation: str,
        start_time: float,
        success: bool,
        items: int = 1,
        cache_hit: bool = False,
        error: Exception | None = None,
    ) -> RepositoryMetrics:
        """Create metrics from operation timing."""
        return cls(
            operation=operation,
            duration_ms=(time.time() - start_time) * 1000,
            success=success,
            items_processed=items,
            cache_hit=cache_hit,
            error_message=str(error) if error else None,
        )


@dataclass
class BatchOperationResult(Generic[T]):
    """Result of a batch repository operation."""

    success: bool
    items_processed: int
    items_failed: int
    results: list[T] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)  # (index, error_message)
    total_duration_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.items_processed + self.items_failed
        if total == 0:
            return 0.0
        return self.items_processed / total

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total


class BaseRepository(ABC, Generic[T, TFilter]):
    """
    Abstract base repository with shared compound engineering features.

    Provides:
    - Batch operation support
    - Metrics collection
    - Error handling with circuit breaker integration
    - Token-efficient context patterns
    - Adversarial review integration points

    Usage:
        class MyRepository(BaseRepository[MyEntity, MyFilter]):
            async def create(self, entity: MyEntity) -> str:
                ...

            async def get(self, entity_id: str) -> MyEntity | None:
                ...

            async def get_all(self, filter_params: MyFilter = None) -> list[MyEntity]:
                ...
    """

    def __init__(self, table_name: str):
        """Initialize base repository.

        Args:
            table_name: SurrealDB table name for this repository
        """
        self._table_name = table_name
        self._metrics: list[RepositoryMetrics] = []
        self._logger = logger.bind(
            repository=self.__class__.__name__,
            table=table_name,
        )

    def _record_metrics(self, metrics: RepositoryMetrics) -> None:
        """Record operation metrics for analysis.

        Compound Engineering: Metrics feed into batch sizing,
        cache optimization, and adversarial review.
        """
        self._metrics.append(metrics)
        # Keep only last 1000 metrics to prevent memory growth
        if len(self._metrics) > 1000:
            self._metrics = self._metrics[-1000:]

        # Log slow operations
        if metrics.duration_ms > 1000:  # > 1 second
            self._logger.warning(
                "Slow repository operation detected",
                operation=metrics.operation,
                duration_ms=metrics.duration_ms,
                items_processed=metrics.items_processed,
            )

    def _get_recent_metrics(
        self, operation: str | None = None, limit: int = 100
    ) -> list[RepositoryMetrics]:
        """Get recent metrics for analysis.

        Used by:
        - Batch sizer for throughput prediction
        - Adversarial review for performance analysis
        - Token efficiency for cache optimization
        """
        if operation:
            filtered = [m for m in self._metrics if m.operation == operation]
            return filtered[-limit:]
        return self._metrics[-limit:]

    async def _execute_with_metrics(
        self,
        operation: str,
        execute_fn,
        items_count: int = 1,
    ) -> Any:
        """Execute operation with automatic metrics collection.

        Args:
            operation: Operation name for metrics
            execute_fn: Async function to execute
            items_count: Number of items being processed

        Returns:
            Result from execute_fn

        Raises:
            Exception: Re-raises any exception from execute_fn
        """
        start_time = time.time()
        try:
            result = await execute_fn()
            metrics = RepositoryMetrics.from_operation(
                operation=operation,
                start_time=start_time,
                success=True,
                items=items_count,
            )
            self._record_metrics(metrics)
            return result
        except Exception as e:
            metrics = RepositoryMetrics.from_operation(
                operation=operation,
                start_time=start_time,
                success=False,
                items=items_count,
                error=e,
            )
            self._record_metrics(metrics)
            self._logger.error(
                f"Repository operation failed: {operation}",
                error=str(e),
                items_count=items_count,
            )
            raise

    async def batch_create(self, items: list[Any]) -> BatchOperationResult[str]:
        """Batch create multiple items.

        Default implementation processes items sequentially.
        Subclasses can override for optimized batch operations.

        Args:
            items: List of items to create

        Returns:
            BatchOperationResult with IDs of created items
        """
        start_time = time.time()
        results = []
        errors = []
        cache_hits = 0
        cache_misses = 0

        for i, item in enumerate(items):
            try:
                # Subclasses should override create()
                if hasattr(self, "create"):
                    result = await self.create(item)
                    results.append(result)
                    cache_misses += 1  # Creates are always misses
                else:
                    errors.append((i, "create() method not implemented"))
            except Exception as e:
                errors.append((i, str(e)))

        return BatchOperationResult(
            success=len(errors) == 0,
            items_processed=len(results),
            items_failed=len(errors),
            results=results,
            errors=errors,
            total_duration_ms=(time.time() - start_time) * 1000,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )

    async def batch_get(self, ids: list[str]) -> BatchOperationResult[T]:
        """Batch retrieve multiple items by ID.

        Default implementation processes items sequentially.
        Subclasses can override for optimized batch operations.

        Args:
            ids: List of item IDs to retrieve

        Returns:
            BatchOperationResult with retrieved items
        """
        start_time = time.time()
        results = []
        errors = []
        cache_hits = 0
        cache_misses = 0

        for i, item_id in enumerate(ids):
            try:
                # Subclasses should override get()
                if hasattr(self, "get"):
                    result = await self.get(item_id)
                    if result is not None:
                        results.append(result)
                        cache_misses += 1
                    else:
                        errors.append((i, "Not found"))
                else:
                    errors.append((i, "get() method not implemented"))
            except Exception as e:
                errors.append((i, str(e)))

        return BatchOperationResult(
            success=len(errors) == 0,
            items_processed=len(results),
            items_failed=len(errors),
            results=results,
            errors=errors,
            total_duration_ms=(time.time() - start_time) * 1000,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of repository metrics.

        Used by:
        - Adversarial review for performance analysis
        - Batch sizer for throughput prediction
        - Monitoring dashboards

        Returns:
            Dictionary with metrics summary
        """
        if not self._metrics:
            return {"total_operations": 0}

        total = len(self._metrics)
        successful = sum(1 for m in self._metrics if m.success)
        failed = total - successful
        avg_duration = sum(m.duration_ms for m in self._metrics) / total
        total_items = sum(m.items_processed for m in self._metrics)
        cache_hits = sum(1 for m in self._metrics if m.cache_hit)

        # Group by operation type
        by_operation: dict[str, list[RepositoryMetrics]] = {}
        for metric in self._metrics:
            if metric.operation not in by_operation:
                by_operation[metric.operation] = []
            by_operation[metric.operation].append(metric)

        operation_stats = {}
        for op, metrics in by_operation.items():
            operation_stats[op] = {
                "count": len(metrics),
                "avg_duration_ms": sum(m.duration_ms for m in metrics) / len(metrics),
                "success_rate": sum(1 for m in metrics if m.success) / len(metrics),
            }

        return {
            "total_operations": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_duration_ms": avg_duration,
            "total_items_processed": total_items,
            "cache_hit_rate": cache_hits / total if total > 0 else 0.0,
            "by_operation": operation_stats,
        }

    def clear_metrics(self) -> None:
        """Clear collected metrics."""
        self._metrics.clear()
