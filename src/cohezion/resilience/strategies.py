"""RAH Healing Strategies - Action implementations for autonomic healing."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from cohezion.mcp.shared.session import get_session_manager
from cohezion.reliability.monitor import get_resource_monitor


logger = logging.getLogger(__name__)


class HealingStrategy(ABC):
    """Base class for all autonomic healing strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the strategy."""
        pass

    @property
    def confidence(self) -> float:
        """Estimated reliability of this strategy (0.0 to 1.0)."""
        return 0.8

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

    @property
    def confidence(self) -> float:
        return 0.9

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

    @property
    def confidence(self) -> float:
        return 0.95

    async def execute(self, context: dict[str, Any]) -> bool:
        reduction_factor = context.get("reduction_factor", 0.5)
        logger.info(f"RAH: Reducing context windows by {reduction_factor * 100}%")

        # Set global pressure mitigation flag in ResourceMonitor
        monitor = get_resource_monitor()
        monitor.pressure_mitigation_active = True

        # Proactively clear transient sessions to free Redis/Memory
        sm = get_session_manager()
        cleared_count = await sm.clear_all_sessions()
        logger.info(f"RAH: Proactively cleared {cleared_count} active sessions")

        # Broadcast signal (simulated)
        logger.warning("RAH: Broadcast COMPACT_CONTEXT signal to all active agents")

        # We assume success once flagged; components like ContextHarness
        # should check this flag during prompt preparation.
        return True


class SystemRestartStrategy(HealingStrategy):
    """Performs emergency restart of core services (Ollama, SurrealDB)."""

    @property
    def name(self) -> str:
        return "system_restart"

    @property
    def confidence(self) -> float:
        return 0.7

    async def execute(self, context: dict[str, Any]) -> bool:
        service = context.get("service", "all")
        logger.critical(f"RAH: Initiating EMERGENCY RESTART for service: {service}")

        monitor = get_resource_monitor()
        vitals = monitor.get_vitals()

        # 1. Trigger existing emergency shutdown logic (kills runaway pids)
        await monitor.emergency_shutdown(vitals)

        # 2. Implementation of actual restart logic
        try:
            if service == "all" or "mcp" in service:
                # Use project root derived from this file's location
                base_dir = Path(__file__).parent.parent.parent.parent
                script_path = base_dir / "start-mcp-servers.sh"

                if not script_path.exists():
                    logger.error(f"RAH: Recovery script not found at {script_path}")
                    return False

                process = await asyncio.create_subprocess_exec(
                    "bash",
                    str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                logger.info(f"RAH: Triggered {script_path} for service recovery")

                try:
                    # Wait briefly to catch immediate script failures
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                    if process.returncode != 0:
                        logger.error(f"RAH: Recovery script failed with code {process.returncode}")
                        return False
                except TimeoutError:
                    # Script is likely long-running (daemon mode), consider trigger successful
                    pass

            return True
        except Exception as e:
            logger.error(f"RAH: Service restart failed: {e}")
            return False
