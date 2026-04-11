"""Autonomous Kaggle Flywheel - Closed-loop AIMO/AGI optimization."""

import asyncio
import logging
import random
import time
from typing import List

from cohezion.research.autoresearch_driver import AutoresearchDriver

# Tracks
TRACKS = ["aimo", "agi"]

async def run_flywheel(max_hours: float = 8.0):
    """Run the autonomous submission loop for a fixed time budget."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("Flywheel")
    
    start_time = time.time()
    max_seconds = max_hours * 3600
    
    logger.info(f"🚀 Initializing Autonomous Kaggle Flywheel (Budget: {max_hours} hours)")
    
    while (time.time() - start_time) < max_seconds:
        elapsed = (time.time() - start_time) / 3600
        logger.info(f"--- Flywheel Status: {elapsed:.2f}/{max_hours} hours elapsed ---")
        
        # 1. Select Track (Random for now, will be UCB1 guided by AutoresearchDriver)
        target = random.choice(TRACKS)
        logger.info(f"🎯 Selected Target: {target}")
        
        # 2. Run Autoresearch Loop for selected track
        # (This will trigger local benchmarks -> Kaggle submissions -> Feedback)
        try:
            driver = AutoresearchDriver(target=target, budget_seconds=1800) # 30 min budget per kernel run
            # Run 1 iteration of the full loop (select -> mutate -> run -> sub -> feedback)
            await driver.run_loop(n_iterations=1)
        except Exception as e:
            logger.error(f"❌ Track {target} failed: {e}")
            
        # 3. Rate limiting (Respect Kaggle 5-subs/day)
        logger.info("💤 Cooling down for 10 minutes...")
        await asyncio.sleep(600)

    logger.info("🏁 Flywheel budget exhausted. Shutting down.")

if __name__ == "__main__":
    # Run for 8 hours (standard overnight mission)
    asyncio.run(run_flywheel(max_hours=8.0))
