"""RAH Autonomic Manager - Core MAPE-K loop implementation."""

import asyncio
import contextlib
import logging
import time
import uuid
from typing import Any

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    UniverseNode,
    get_surreal_client,
)
from cohezion.reliability.monitor import get_resource_monitor

from .strategies import (
    ContextReductionStrategy,
    HealingStrategy,
    ModelSwapStrategy,
    SystemRestartStrategy,
)


logger = logging.getLogger(__name__)


class AutonomicManager:
    """
    Central manager for Resilience & Autonomic Healing (RAH).
    Implements the MAPE-K control loop with SurrealDB persistence.
    """

    def __init__(self):
        self._monitor = get_resource_monitor()
        self._surreal = get_surreal_client()
        self._strategies: dict[str, HealingStrategy] = {
            "model_swap": ModelSwapStrategy(),
            "context_reduction": ContextReductionStrategy(),
            "system_restart": SystemRestartStrategy(),
        }
        self._running = False
        self._loop_task: asyncio.Task | None = None
        self.last_action_time = 0
        self.cooldown_seconds = 300

    async def start(self, interval_seconds: int = 10):
        """Start the autonomic healing loop."""
        if self._running:
            return
        self._running = True

        # Ensure surreal connection
        try:
            await self._surreal.connect()
        except Exception as e:
            logger.error(
                f"RAH: Failed to connect to SurrealDB: {e}. Decisions will not be persisted."
            )

        self._loop_task = asyncio.create_task(self._run_loop(interval_seconds))
        logger.info("RAH: Autonomic Manager started")

    async def stop(self):
        """Stop the autonomic healing loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task
        logger.info("RAH: Autonomic Manager stopped")

    async def _run_loop(self, interval: int):
        """Internal MAPE-K execution loop."""
        while self._running:
            try:
                # 1. MONITOR
                vitals = self._monitor.get_vitals()

                # 2. ANALYZE
                analysis = self._analyze_vitals(vitals)

                # 3. PLAN & EXECUTE
                if analysis.get("action_needed"):
                    if time.time() - self.last_action_time > self.cooldown_seconds:
                        await self._execute_healing(analysis, vitals)
                        self.last_action_time = time.time()
                    else:
                        logger.debug("RAH: Action needed but manager is in cooldown")

            except Exception as e:
                logger.error(f"RAH: Loop error: {e}")

            await asyncio.sleep(interval)

    def _analyze_vitals(self, vitals: dict[str, Any]) -> dict[str, Any]:
        """Analyze system vitals to determine if healing is needed."""
        cpu = vitals.get("cpu_percent", 0)
        ram = vitals.get("memory_percent", 0)
        vram = vitals.get("vram_percent", 0)

        analysis = {"action_needed": False, "strategy": None, "context": {}}

        # Proactive logic hierarchy based on severity
        if cpu > 95 or ram > 95 or vram > 95:
            analysis["action_needed"] = True
            analysis["strategy"] = "system_restart"
            analysis["context"] = {"reason": "Critical pressure", "vitals": vitals}
        elif ram > 85 or vram > 85:
            analysis["action_needed"] = True
            analysis["strategy"] = "context_reduction"
            analysis["context"] = {"reduction_factor": 0.6}
        elif cpu > 80:
            analysis["action_needed"] = True
            analysis["strategy"] = "model_swap"
            analysis["context"] = {"target_model": "phi3:mini"}

        return analysis

    async def _execute_healing(self, analysis: dict[str, Any], vitals: dict[str, Any]):
        """Execute the planned healing strategy and log to SurrealDB."""
        strategy_name = analysis.get("strategy")
        strategy = self._strategies.get(strategy_name)

        if not strategy:
            logger.warning(f"RAH: Unknown strategy requested: {strategy_name}")
            return

        logger.warning(f"RAH: Executing healing strategy: {strategy_name}")
        success = await strategy.execute(analysis.get("context", {}))

        # Log decision to SurrealDB with strategy confidence
        await self._log_decision(strategy, success, analysis, vitals)

        if success:
            logger.info(f"RAH: Strategy {strategy_name} executed successfully")
        else:
            logger.error(f"RAH: Strategy {strategy_name} execution failed")

    async def _log_decision(
        self, strategy: HealingStrategy, success: bool, analysis: dict, vitals: dict
    ):
        """Persist RAH decision to SurrealDB."""
        try:
            node_id = f"rah_{uuid.uuid4()}"
            content = f"RAH Decision: {strategy.name} | Success: {success}"

            # Map vitals to 12D physics state for visualization
            # Use strategy's base confidence as the 'logic' value
            physics = PhysicsState(
                x=vitals.get("cpu_percent", 0) / 100.0,
                y=vitals.get("memory_percent", 0) / 100.0,
                z=vitals.get("vram_percent", 0) / 100.0,
                control=1.0 if success else 0.0,
                logic=strategy.confidence if success else 0.1,
                time=time.time(),
            )

            node = UniverseNode(
                id=node_id,
                content=content,
                node_type="rah_decision",
                physics_state=physics,
                metadata={
                    "strategy": strategy.name,
                    "success": success,
                    "analysis": analysis,
                    "vitals": vitals,
                },
            )

            await self._surreal.store_node(node)
            logger.debug(f"RAH: Decision persisted to SurrealDB: {node_id}")
        except Exception as e:
            logger.error(f"RAH: Failed to persist decision to SurrealDB: {e}")


# Singleton instance
_instance: AutonomicManager | None = None


def get_rah_manager() -> AutonomicManager:
    """Get the global AutonomicManager instance."""
    global _instance
    if _instance is None:
        _instance = AutonomicManager()
    return _instance
