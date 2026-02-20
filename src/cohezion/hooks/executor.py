"""
Hook execution engine.

Attribution: Execution model inspired by Pilot's hook pipeline
Implementation: Original COHEZION design with JourneyTracker integration
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from .events import HookEvent
from .registry import HookRegistry

logger = logging.getLogger(__name__)


class HookExecutor:
    """Executes registered hooks for lifecycle events.

    Integrates with JourneyTracker for persistence and GlobalMetricsAggregator
    for quality monitoring.

    Attribution: Inspired by Pilot's hook execution model
    """

    def __init__(
        self,
        registry: HookRegistry,
        journey_tracker: Optional[Any] = None,
        metrics_aggregator: Optional[Any] = None,
    ) -> None:
        """Initialize hook executor.

        Args:
            registry: Hook registry containing registered hooks
            journey_tracker: Optional JourneyTracker for 12D persistence
            metrics_aggregator: Optional GlobalMetricsAggregator for quality tracking
        """
        self._registry = registry
        self._journey_tracker = journey_tracker
        self._metrics = metrics_aggregator
        self._execution_count: Dict[HookEvent, int] = {}

    async def execute(
        self,
        event: HookEvent,
        context: Optional[Dict[str, Any]] = None,
        fail_fast: bool = True,
    ) -> Dict[str, Any]:
        """Execute all hooks for a lifecycle event.

        Args:
            event: The lifecycle event that triggered hooks
            context: Event-specific context data
            fail_fast: If True, stop on first blocking hook failure

        Returns:
            Dictionary with execution results
        """
        hooks = self._registry.get_hooks(event)
        if not hooks:
            logger.debug(f"No hooks registered for {event}")
            return {"event": event, "executed": 0, "failures": []}

        results = {
            "event": event,
            "executed": 0,
            "failures": [],
            "context": context or {},
        }

        logger.info(f"Executing {len(hooks)} hooks for {event}")

        for hook_fn in hooks:
            try:
                # Check if hook is async
                if asyncio.iscoroutinefunction(hook_fn):
                    await hook_fn(context or {})
                else:
                    hook_fn(context or {})

                results["executed"] += 1

            except Exception as e:
                logger.error(f"Hook failed for {event}: {e}")
                results["failures"].append(str(e))

                # Blocking hooks must succeed
                hook_id = getattr(hook_fn, "__name__", "unknown")
                if self._registry.is_blocking(hook_id) and fail_fast:
                    logger.critical(f"Blocking hook {hook_id} failed, aborting")
                    break

        # Track execution in journey if available
        if self._journey_tracker:
            try:
                self._journey_tracker.record_hook_execution(
                    event=event, results=results
                )
            except Exception as e:
                logger.warning(f"Failed to track hook execution: {e}")

        # Update metrics if available
        if self._metrics:
            try:
                self._metrics.record_hook_execution(
                    event=event, success=len(results["failures"]) == 0
                )
            except Exception as e:
                logger.warning(f"Failed to record hook metrics: {e}")

        self._execution_count[event] = self._execution_count.get(event, 0) + 1
        return results

    def get_execution_stats(self) -> Dict[HookEvent, int]:
        """Get hook execution statistics."""
        return self._execution_count.copy()
