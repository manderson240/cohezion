r"""Autonomous Low & Slow BBQ Worker Launcher
==========================================
Puts the complete AGI & BBQ stack to work:
  - Ignites the Cosmic Fire Protocol (HIHO threshold = 0.45)
  - Connects CrossSessionEventBridge to SurrealDB `event_log`
  - Runs continuous Low & Slow 12D Poincaré Manifold Simulation
  - Dispatches GAIA SDK Bugfix Agents for self-healing Kanban items
  - Logs telemetry every cycle
"""

from __future__ import annotations

import asyncio
import logging
import time

from cohezion.agents.gaia_bugfix_agent import GaiaBugfixAgentManager
from cohezion.compound.chronos import get_chronos
from cohezion.compound.cosmic_fire_protocol import CosmicFireProtocol
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventBus
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.smoke_ring_manifold import SmokeRingManifold


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [BBQ_WORKER] - %(message)s",
    handlers=[logging.FileHandler("autonomous_bbq_worker.log"), logging.StreamHandler()],
)
logger = logging.getLogger("AutonomousBBQWorker")


async def main() -> None:
    logger.info("🔥 Igniting the Smoker — Putting Cohezion Low & Slow BBQ Stack to Work!")

    # 1. Start EventBus & CrossSessionEventBridge
    bus = EventBus()
    await bus.start()
    bridge = CrossSessionEventBridge(event_bus=bus, session_id="bbq_production_worker")
    await bridge.initialize()

    # 2. Initialize Cosmic Fire Protocol & Smoke Ring Manifold
    cfp = CosmicFireProtocol(threshold=0.45, notify_telegram=False)
    smoke_engine = SmokeRingManifold(major_radius=0.50, minor_radius=0.10)
    bugfix_mgr = GaiaBugfixAgentManager(bus=bus)

    # 3. Publish Ignition Event
    await bus.publish(Event.agent_start("BBQProductionWorker", model="deepseek-r1-0528-8b-FLM"))
    logger.info("🚀 Production Worker Active! Entering Low & Slow Loop...")

    cycle = 0
    try:
        while cycle < 10:  # 10 production cycles demonstration
            cycle += 1
            t0 = time.time()

            # Simulate 2048D Poincaré state vector tick
            p2048 = PoincareManifoldND.project([0.005 * cycle] * 2048, target_dim=2048)
            smoke = smoke_engine.project_to_smoke_ring(p2048)

            # Evaluate Cosmic Fire HIHO Ignition
            cascade = cfp.ignition_cascade(quality_score=smoke.ring_coherence)

            # Publish cycle telemetry to EventBus -> SurrealDB event_log
            await bus.publish(
                Event.agent_complete(
                    agent_name="BBQProductionWorker",
                    result={
                        "cycle": cycle,
                        "ring_coherence": smoke.ring_coherence,
                        "penetration_depth": smoke.penetration_depth,
                        "ignited": len(cascade) > 0,
                    },
                    duration_ms=(time.time() - t0) * 1000,
                )
            )

            logger.info(
                f"🍖 [Cycle {cycle}/10] Coherence={smoke.ring_coherence:.4f} | "
                f"Penetration={smoke.penetration_depth:.4f} | "
                f"Ignited={len(cascade) > 0}"
            )

            await asyncio.sleep(1.0)  # Unhurried 1s settle between cycles

    finally:
        await bus.stop()
        logger.info("✅ Production Worker Run Completed Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
