#!/usr/bin/env python3
"""
COHEZION OVERNIGHT AUTONOMOUS RESEARCH SPRINT (Self-Healed)
==============================================
Grounded in existing src/cohezion components.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.swarm.compound_client import get_compound_client
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine
from cohezion.core.persistence.surreal_client import SurrealClient
import trackio

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("OvernightMission")

class OvernightMission:
    def __init__(self):
        self.client = get_compound_client()
        self.engine = HihoVectorEngine(num_rounds=1_000_000)
        self.surreal = SurrealClient(url="ws://localhost:8000/rpc", namespace="cohezion", database="universe")
        self.end_time = datetime.now() + timedelta(hours=8)

    async def run_cycle(self, iteration):
        logger.info(f"🌌 Starting Cycle {iteration}...")
        
        # 1. Physics Simulation
        results = self.engine.run_simulation()
        stability = results.get("mean_stability", 0.0)
        logger.info(f"Simulation Complete. Stability: {stability:.4f}")
        
        # 2. Persist to SurrealDB
        await self.surreal.connect()
        await self.surreal.create("simulations", {
            "iteration": iteration,
            "stability": stability,
            "timestamp": datetime.now().isoformat()
        })
        
        # 3. Slm Research (Analyze stability patterns)
        prompt = f"""
        Analyze these 12D simulation results:
        Stability: {stability:.4f}
        
        Instruction:
        - Identify one 'Stabilization Pattern' for the 12D manifold.
        - Propose a 'Compound Engineering' learning.
        - Format as a Learning for KEY_LEARNINGS.md.
        """
        response = await self.client.generate(prompt, task_type="analysis")
        
        # 4. Log to Trackio
        trackio.log({"iteration": iteration, "stability": stability})
        
        # 5. Append Learning (Manifestation)
        with open(PROJECT_ROOT / "src/cohezion/knowledge_graph/KEY_LEARNINGS.md", "a") as f:
            f.write(f"\n### Overnight Learning (Iteration {iteration})\n{response}\n")
            
        logger.info(f"✅ Cycle {iteration} Complete.")

    async def main_loop(self):
        trackio.init(project="cohezion-core", space_id="manderson240/cohezion-trackio")
        iteration = 1
        while datetime.now() < self.end_time:
            try:
                await self.run_cycle(iteration)
                iteration += 1
            except Exception as e:
                logger.error(f"Cycle failed: {e}")
            
            # Breathe between cycles
            await asyncio.sleep(600) # 10 min break
            
        trackio.finish()

if __name__ == "__main__":
    mission = OvernightMission()
    asyncio.run(mission.main_loop())
