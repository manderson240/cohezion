"""
Journey Worker: Persistent consumer for FlumeJourneyEvents.
Handles SurrealDB persistence, Ouroboros bridging, and active healing.
"""

from __future__ import annotations

import logging
import asyncio
from cohezion.core.telemetry_bus import get_telemetry_bus
from cohezion.data_mesh.journey_telemetry import FlumeJourneyEvent
from cohezion.reliability import get_circuit
from cohezion.storage.surreal_client import SurrealDBClient, TrajectoryNode
from cohezion.physics.ouroboros_bridge import OuroborosBridge

logger = logging.getLogger(__name__)

class JourneyWorker:
    """
    Background worker that processes telemetry events from the bus.
    """
    
    def __init__(self):
        self._bus = get_telemetry_bus()
        self._db = SurrealDBClient()
        self._bridge = OuroborosBridge()
        self._running = False

    async def start(self):
        """Register with the bus and start processing."""
        if self._running:
            return
        self._running = True
        
        # Connect to DB
        await self._db.connect()
        
        # Subscribe to telemetry events
        self._bus.subscribe(self.process_event)
        logger.info("👷 Journey Worker active (Monitoring HIHO stability)")

    async def process_event(self, event: FlumeJourneyEvent):
        """
        Main processing logic for each journey event.
        """
        # 1. Persist to SurrealDB (Wrapped in reliability circuit)
        circuit = get_circuit("surrealdb")
        if circuit.allow_request():
            try:
                node = TrajectoryNode(
                    evo_id=event.journey_id,
                    dimension_state=event.state_12d,
                    coherence=event.coherence,
                    timestamp=str(event.timestamp)
                )
                await self._db.insert_trajectory_node(node)
                circuit.record_success()
            except Exception as e:
                logger.error("❌ Worker failed SurrealDB persistence: %s", e)
                circuit.record_failure()
        else:
            logger.debug("🛰️ SurrealDB circuit OPEN - skipping telemetry persistence")

        # 2. Pipe to Ouroboros Bridge for failure analysis
        try:
            # check_coherence expects a drop threshold, we provide (1.0 - current)
            drop = abs(0.5 - event.coherence)
            await self._bridge.check_coherence(drop, task_id=event.journey_id)
        except Exception as e:
            logger.debug("Ouroboros bridge skip: %s", e)

        # 3. Active Healing Trigger
        if abs(event.coherence - 0.5) > 0.3: # Threshold from spec
            logger.warning("🚨 HIHO DRIFT DETECTED: Triggering Healing System for %s", event.journey_id)
            try:
                from cohezion.healing import get_healing_system
                healer = get_healing_system()
                # Healer runs autonomously in background
                await healer.heal_manifold(event.journey_id, event.state_12d)
            except ImportError:
                logger.debug("Healing system not available in this context.")

# Singleton
_WORKER = None

def get_journey_worker() -> JourneyWorker:
    global _WORKER
    if _WORKER is None:
        _WORKER = JourneyWorker()
    return _WORKER
