#!/usr/bin/env python3
"""
COHEZION OVERNIGHT AUTONOMOUS RESEARCH SPRINT (Verified TDD Edition)
==============================================
Grounded in EnhancedSimulator (FLUME + R-Zero).
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path


# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import trackio

from cohezion.simulation.enhanced_simulator import EnhancedSimulator
from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("OvernightMission")


class OvernightMission:
    def __init__(self):
        self.simulator = EnhancedSimulator()
        self.client = get_compound_client()
        self.end_time = datetime.now() + timedelta(hours=8)

    async def run_cycle(self, iteration):
        logger.info(f"🌌 Starting Cycle {iteration}...")

        # 1. Physics Simulation (Using R-Zero Enhanced Triad)
        # We run a batch of 10 simulations across different streams
        results = await self.simulator.run_batch(10)

        stats = self.simulator.get_stats()
        stability = stats.get("avg_score", 0.0)
        logger.info(f"Batch Complete. Avg Stability: {stability:.4f}")

        # 2. Slm Research (Analyze stability patterns)
        prompt = f"""
        Analyze these 12D simulation results from our R-Zero Triad:
        Avg Stability: {stability:.4f}
        Approved Ratio: {stats.get("approval_rate", 0):.2f}
        
        Instruction:
        - Identify one 'Manifold Convergence' pattern.
        - Propose a 'Compound Engineering' learning.
        - Format as a Learning for KEY_LEARNINGS.md.
        """
        response, tokens = await self.client.generate(prompt)

        # 3. Log to Trackio
        trackio.log(
            {
                "iteration": iteration,
                "stability": stability,
                "difficulty": stats.get("current_difficulty", 1.0),
            }
        )

        # 4. Append Learning (Manifestation) — sanitize LLM output
        sanitized = response[:5000].replace("Instruction:", "").replace("System:", "")
        with open(PROJECT_ROOT / "src/cohezion/knowledge_graph/KEY_LEARNINGS.md", "a") as f:
            f.write(f"\n### Overnight Learning (Iteration {iteration})\n{sanitized}\n")

        logger.info(f"✅ Cycle {iteration} Complete.")

    async def main_loop(self):
        trackio.init(project="cohezion-core")
        iteration = 1
        while datetime.now() < self.end_time:
            try:
                await self.run_cycle(iteration)
                iteration += 1
            except Exception as e:
                logger.error(f"Cycle failed: {e}", exc_info=True)

            # Breathe between cycles
            await asyncio.sleep(600)  # 10 min break

        trackio.finish()


if __name__ == "__main__":
    mission = OvernightMission()
    asyncio.run(mission.main_loop())
