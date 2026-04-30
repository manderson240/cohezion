"""Elegant unified batch processor.

Replaces batch_executor.py (648 lines) + batch_sizer.py (567 lines)
with single clean implementation.
Total: 1,215 lines → ~200 lines
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from cohezion.compound.models import (
    BatchConfig,
    ExecutionContext,
    ExecutionResult,
    Task,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of batch processing."""

    results: list[ExecutionResult] = field(default_factory=list)
    failed_tasks: list[Task] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        successful = sum(1 for r in self.results if r.success)
        return successful / len(self.results)


class BatchProcessor:
    """Unified batch processing.

    Clean implementation vs the complex multi-phase batch_executor.
    """

    def __init__(
        self,
        executor: Callable[[Task, ExecutionContext], ExecutionResult],
        config: BatchConfig | None = None,
    ):
        self.executor = executor
        self.config = config or BatchConfig()
        self._queue: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add task to batch queue."""
        self._queue.append(task)

    def should_execute(self) -> bool:
        """Check if we have enough tasks to execute."""
        return len(self._queue) >= self.config.optimal_batch_size

    async def process_batch(self) -> BatchResult:
        """Process current batch of tasks."""
        if not self._queue:
            return BatchResult()

        # Take optimal batch size
        batch_size = min(len(self._queue), self.config.max_batch_size)
        batch = self._queue[:batch_size]
        self._queue = self._queue[batch_size:]

        logger.info(f"Processing batch of {len(batch)} tasks")

        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def execute_with_limit(task: Task) -> ExecutionResult:
            async with semaphore:
                context = ExecutionContext(
                    session_id=f"batch-{task.id}",
                    task=task,
                )
                # Run in thread pool for sync executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.executor, task, context)

        # Execute all tasks
        tasks = [execute_with_limit(t) for t in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        batch_result = BatchResult()
        for task, result in zip(batch, results, strict=True):
            if isinstance(result, Exception):
                batch_result.results.append(
                    ExecutionResult(
                        success=False,
                        output=str(result),
                        error_type=type(result).__name__,
                        error_message=str(result),
                    )
                )
                batch_result.failed_tasks.append(task)
            else:
                batch_result.results.append(result)
                if not result.success:
                    batch_result.failed_tasks.append(task)

        logger.info(
            f"Batch complete: {len(batch_result.results)} tasks, "
            f"{batch_result.success_rate:.1%} success rate"
        )

        return batch_result

    def process_sync(self) -> BatchResult:
        """Synchronous batch processing."""
        return asyncio.run(self.process_batch())

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self._queue)

    def clear_queue(self) -> None:
        """Clear all queued tasks."""
        self._queue.clear()


class SimpleBatch:
    """Minimal batch processor for basic use cases."""

    def __init__(
        self,
        executor: Callable[[Task, ExecutionContext], ExecutionResult],
    ):
        self.executor = executor

    def process(self, tasks: list[Task]) -> list[ExecutionResult]:
        """Process tasks sequentially."""
        results = []
        for task in tasks:
            context = ExecutionContext(
                session_id=f"simple-{task.id}",
                task=task,
            )
            result = self.executor(task, context)
            results.append(result)
        return results
