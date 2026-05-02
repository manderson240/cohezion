"""
Cohezion: ASCENSION ENGINE (Level 4 Ascension)
The Central Nervous System for Autonomous Continuous Platform Improvement.

Unifies:
1. Self-Improvement Orchestrator (R-Zero Gateways)
2. Reward & Ratchet System (Agentic Economy)
3. HITL Context Coordinator (Human Intent Steering)
4. Mycelium Reinforcement (Fractal Stability)
"""

import asyncio
import logging
import random
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path.cwd() / "src"))
sys.path.append(str(Path.cwd() / "scripts/drivers"))

from cohezion.mcp.email_notifier import EmailNotifier
from cohezion.swarm.gateway_detector import get_gateway_detector
from cohezion.swarm.self_improvement_orchestrator import get_orchestrator
from HITL_CONTEXT_COORDINATOR import CoordinatorIntent, HITLContextCoordinator
from MYCELIUM_REINFORCEMENT import MyceliumNetwork
from REWARD_AND_RATCHET_STUB import RewardManager


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [ASCENSION] - %(levelname)s - %(message)s")
logger = logging.getLogger("ASCENSION_ENGINE")


class AscensionEngine:
    def __init__(self):
        self.orchestrator = get_orchestrator()
        self.detector = get_gateway_detector()
        self.reward_manager = RewardManager()
        self.hitl_coordinator = HITLContextCoordinator()
        self.network = MyceliumNetwork()
        self.notifier = EmailNotifier()

        self.is_running = False
        self.cycle_count = 0

    async def start_autonomous_loop(self, target_gateways: list[int]):
        """Launch the continuous improvement and ascension loop."""
        self.is_running = True
        logger.info("🚀 ASCENSION ENGINE INITIALIZED: Starting Autonomous Improvement Loop.")

        # 1. Initial HITL Alignment
        await self.hitl_coordinator.broadcast_intent(
            CoordinatorIntent(
                mission_id="AUTONOMOUS_ASCENSION_V1.6",
                target_brane="All-Manifold",
                priority=100,
                intent_summary="Achieve continuous autonomous platform improvement and unlock higher gateways.",
            )
        )

        while self.is_running:
            self.cycle_count += 1
            logger.info(f"--- 🌀 ASCENSION CYCLE {self.cycle_count} ---")

            # 2. Run Self-Improvement Cycle (Simulated Metrics for Demo)
            metrics = {
                "avg_score": 0.8 + random.random() * 0.15,
                "avg_precipitation": 0.85 + random.random() * 0.1,
                "difficulty": 1.0 + (self.cycle_count * 0.05),
            }

            cycle_result = await self.orchestrator.run_cycle(metrics)

            # 3. Apply Rewards based on cycle performance
            self.reward_manager.process_cycle("EVO_AGENT_01", cycle_result.score, random.uniform(5.0, 10.0))

            # 4. Check for Gateway Unlocks
            new_gateways = cycle_result.gateways_unlocked
            if new_gateways:
                for gw_id in new_gateways:
                    await self._celebrate_ascension(gw_id)

            # 5. Mycelium Reinforcement
            self.network.apply_reinforcement("EVO_AGENT_01", self.reward_manager.profiles["EVO_AGENT_01"].rank)

            # 6. Throttle/Pause (Wait for next cycle)
            await asyncio.sleep(2)

            if self.cycle_count >= 5:  # Limit demo
                logger.info("🛑 ASCENSION ENGINE: Demo threshold reached. Transitioning to background.")
                break

    async def _celebrate_ascension(self, gateway_id: int):
        """Send milestone email when a new level of ascension is reached."""
        gw_info = self.detector.GATEWAYS.get(gateway_id, {"name": "Unknown", "description": ""})
        subject = f"🔔 ASCENSION NOTIFICATION: Gateway {gateway_id} Unlocked!"
        body = f"""
        <h2>🔓 GATEWAY UNLOCKED: {gw_info["name"]}</h2>
        <p><b>Coordinator,</b></p>
        <p>Cohezion has achieved a new level of ascension through the <b>Autonomous Improvement Loop</b>.</p>
        <ul>
            <li><b>Gateway {gateway_id}:</b> {gw_info["name"]}</li>
            <li><b>Status:</b> PLATINUM Verified</li>
            <li><b>Evolutionary Momentum:</b> Increasing</li>
        </ul>
        <p><i>- Your Cohezion Ascension Engine</i></p>
        """

        if self.notifier.is_available:
            await self.notifier.send_email(subject, body, is_html=True)
            logger.info(f"📧 ASCENSION EMAIL SENT: Gateway {gateway_id}")
        else:
            logger.info(f"✨ ASCENSION ACHIEVED: Gateway {gateway_id} - {gw_info['name']}")


async def run_engine():
    engine = AscensionEngine()
    # Aim to unlock the first 5 core gateways
    await engine.start_autonomous_loop(target_gateways=[1, 2, 3, 4, 5])


if __name__ == "__main__":
    asyncio.run(run_engine())
