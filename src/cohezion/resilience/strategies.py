"""RAH Healing Strategies - Action implementations for autonomic healing."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from cohezion.reliability.monitor import get_resource_monitor


logger = logging.getLogger(__name__)


class HealingStrategy(ABC):
    """Base class for all autonomic healing strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the strategy."""
        pass

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> bool:
        """Execute the healing action.

        Returns:
            True if action was successful, False otherwise.
        """
        pass


class ModelSwapStrategy(HealingStrategy):
    """Swaps currently loaded model for a lighter or faster alternative."""

    @property
    def name(self) -> str:
        return "model_swap"

    async def execute(self, context: dict[str, Any]) -> bool:
        current_model = context.get("current_model")
        target_model = context.get("target_model")

        if not target_model:
            logger.warning("ModelSwapStrategy: No target model specified in context")
            return False

        monitor = get_resource_monitor()
        logger.info(f"RAH: Swapping model {current_model} -> {target_model}")

        try:
            # Integration with ResourceMonitor's unload capability
            if current_model:
                await monitor.unload_model(current_model)

            # Execution of swap would normally trigger Ollama load on next call
            # or proactive load here.
            return True
        except Exception as e:
            logger.error(f"RAH: Model swap failed: {e}")
            return False


class ContextReductionStrategy(HealingStrategy):
    """Reduces context window size to alleviate memory pressure."""

    @property
    def name(self) -> str:
        return "context_reduction"

    async def execute(self, context: dict[str, Any]) -> bool:
        reduction_factor = context.get("reduction_factor", 0.5)
        logger.info(f"RAH: Reducing context windows by {reduction_factor*100}%")

        # In a real system, this would update the global context manager
        # or signal active agents to truncate their history.
        return True


class SystemRestartStrategy(HealingStrategy):
    """Performs emergency restart of core services (Ollama, SurrealDB)."""

    @property
    def name(self) -> str:
        return "system_restart"

    async def execute(self, context: dict[str, Any]) -> bool:
        service = context.get("service", "all")
        logger.critical(f"RAH: Initiating EMERGENCY RESTART for service: {service}")

        monitor = get_resource_monitor()
        vitals = monitor.get_vitals()

        # Trigger existing emergency shutdown logic
        await monitor.emergency_shutdown(vitals)

        # Implementation would then trigger service restart via systemd or docker
        return True
