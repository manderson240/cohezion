"""Elegant simplified compound executor.

Replaces the 1,106-line monster with a clean, focused implementation.
Single responsibility: execute tasks with optional analysis.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cohezion.compound.models import (
    AnalysisReport,
    ExecutionContext,
    ExecutionMetrics,
    ExecutionResult,
    Task,
)


logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """Configuration for execution."""

    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_analysis: bool = True
    enable_checkpointing: bool = True


class CompoundExecutor:
    """Clean, focused executor.

    Single responsibility: execute tasks with optional analysis.
    No god object - accepts analyzers and persisters as plugins.
    """

    def __init__(
        self,
        execute_fn: Callable[[Task, dict[str, Any]], tuple[str, dict[str, Any]]],
        config: ExecutionConfig | None = None,
        analyzer: Callable[[ExecutionResult, Task], AnalysisReport] | None = None,
        persister: Callable[[ExecutionContext, ExecutionResult], None] | None = None,
    ):
        """Initialize with minimal dependencies.

        Args:
            execute_fn: Core execution logic (task, context) -> (output, metrics)
            config: Execution configuration
            analyzer: Optional post-execution analysis
            persister: Optional vault persistence
        """
        self.execute_fn = execute_fn
        self.config = config or ExecutionConfig()
        self.analyzer = analyzer
        self.persister = persister

    def execute(
        self,
        task: Task,
        context: ExecutionContext | None = None,
    ) -> ExecutionResult:
        """Execute task with retry logic.

        Clean implementation vs the 1,106-line monster.
        """
        if context is None:
            context = ExecutionContext(
                session_id=f"session-{id(task)}",
                task=task,
            )

        # Attempt execution with retries
        for attempt in range(self.config.max_retries + 1):
            context.attempt_number = attempt

            result = self._attempt_execution(task, context)

            if result.success:
                return self._finalize_success(result, context)

            if attempt == self.config.max_retries:
                return self._finalize_failure(result, context)

            # Retry logic
            logger.warning(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(self.config.retry_delay_seconds)
            context = context.with_retry()

        # Should never reach here
        return result

    def _attempt_execution(
        self,
        task: Task,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Single execution attempt."""
        start_time = time.time()

        try:
            # Execute user-provided function
            output, metrics_dict = self.execute_fn(task, context)

            duration = time.time() - start_time

            return ExecutionResult(
                success=True,
                output=output,
                metrics=ExecutionMetrics(
                    duration_seconds=duration,
                    **metrics_dict,
                ),
            )

        except Exception as e:
            duration = time.time() - start_time

            return ExecutionResult(
                success=False,
                output=str(e),
                metrics=ExecutionMetrics(duration_seconds=duration),
                error_type=type(e).__name__,
                error_message=str(e),
            )

    def _finalize_success(
        self,
        result: ExecutionResult,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Finalize successful execution."""
        # Run analysis if configured
        if self.config.enable_analysis and self.analyzer:
            report = self.analyzer(result, context.task)

            if report.retry_recommended and context.attempt_number < self.config.max_retries:
                # Trigger retry via exception (simplified flow)
                logger.info("Analysis recommends retry")
                return self._trigger_retry(result, context)

        # Persist if configured
        if self.config.enable_checkpointing and self.persister:
            self.persister(context, result)

        return result

    def _finalize_failure(
        self,
        result: ExecutionResult,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Finalize failed execution after all retries."""
        logger.error(f"Task failed after {self.config.max_retries + 1} attempts")

        # Persist failure for analysis
        if self.config.enable_checkpointing and self.persister:
            self.persister(context, result)

        return result

    def _trigger_retry(
        self,
        last_result: ExecutionResult,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Trigger a retry with modified context."""
        # Simplified: just try again
        logger.info("Retrying with analysis guidance")
        return self.execute(context.task, context.with_retry())


# Convenience function for simple executions
def execute_simple(
    task_description: str,
    execute_fn: Callable[[], str],
) -> ExecutionResult:
    """Execute simple task without complex setup.

    For one-off executions without retry or analysis.
    """
    start_time = time.time()

    try:
        output = execute_fn()
        duration = time.time() - start_time

        return ExecutionResult(
            success=True,
            output=output,
            metrics=ExecutionMetrics(duration_seconds=duration),
        )
    except Exception as e:
        duration = time.time() - start_time

        return ExecutionResult(
            success=False,
            output=str(e),
            metrics=ExecutionMetrics(duration_seconds=duration),
            error_type=type(e).__name__,
        )
