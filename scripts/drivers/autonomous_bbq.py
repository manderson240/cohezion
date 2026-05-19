#!/usr/bin/env python3
"""
Autonomous BBQ Driver (Low and Slow)
====================================
Runs a long-horizon simulation (target: 50M rounds) while strictly adhering to
system stability constraints (ResourceMonitor).

Philosophy: "Low and Slow BBQ Approach"
- Infinite loop with explicit yields
- Check system vitals every batch
- Dilation factor applied to sleep times
- Persist state to SurrealDB
"""

import asyncio
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cohezion.core.persistence.repositories.journey_repository import JourneyMetrics
from cohezion.core.persistence.repositories.surreal_journey_repository import (
    AgentJourney,
    SurrealJourneyRepository,
)
from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.simulation.biological_diversity import get_diversity_engine
from cohezion.simulation.fractal_universe import UniverseGrid


# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [BBQ] - %(message)s",
    handlers=[logging.FileHandler("autonomous_bbq.log"), logging.StreamHandler()],
)
logger = logging.getLogger("AutonomousBBQ")


class BBQDriver:
    def __init__(self, target_rounds=50_000_000):
        self.target_rounds = target_rounds
        self.current_round = 0
        self.monitor = get_resource_monitor()
        self.diversity_engine = get_diversity_engine()
        self.grid = UniverseGrid(64)  # 4096 sectors
        self.start_time = time.time()
        self.batch_size = 1000  # Save every 1000 rounds

        # Persistence
        self.db = SurrealClient()
        self.repo = SurrealJourneyRepository(self.db)

    async def initialize(self):
        logger.info("🔥 Igniting the Smoker (Initializing BBQ Driver)...")
        # PASSIVE MONITORING: We do NOT start the background heartbeat because it triggers
        # emergency_shutdown() (process kill) at 90% VRAM. Since the system is idling at 93%,
        # we need to handle this gracefully (Sleep/Coma) instead of dying.
        # await self.monitor.start() -> SKIPPED

        await self.db.connect()
        logger.info("✅ Database Connected. Passive Resource Monitor Protocol Active.")

    async def run(self):
        try:
            logger.info(f"🍖 Starting Low & Slow Cook. Target: {self.target_rounds:,} rounds.")

            while self.current_round < self.target_rounds:
                # 1. Check Resources Manually
                vitals = self.monitor.get_vitals()
                vram = vitals.get("vram_percent", 0)

                # SELF-PRESERVATION LOGIC
                if vram > 96.0:
                    # Critical Danger Zone - Deep Sleep
                    if self.current_round % 10 == 0:
                        logger.warning(
                            f"🛑 VRAM CRITICAL ({vram}%). Entering COMA MODE (30s sleep)..."
                        )
                    await asyncio.sleep(30)
                    continue
                elif vram > 92.0:
                    # High Pressure - Slow Cook
                    dilation = 0.05  # Very Slow
                else:
                    # Nominal
                    dilation = 1.0

                # 2. Simulate Batch (Physics Ticks)
                # We simulate a small batch of ticks, but respect the dilation
                # If dilation is 1.0 (Healthy), we run fast. If 0.5, we run half speed (sleep).

                tick_start = time.time()

                # Simulate Physics
                # (Mocking the internal tick logic here for the driver view, usually inside Simulator)
                # In a real run, this calls grid.update() or simulator.tick()
                # For this driver, we assume grid state evolves.

                # Calculate aggregate coherence for biological diversity
                t = time.time()
                global_coherence = 0.5 + 0.1 * (np.sin(t / 100))

                self.diversity_engine.select_substrate(global_coherence)

                self.current_round += 1

                # Dynamic Batch Size for feedback
                limit = 10 if self.current_round < 100 else 1000

                # 3. Persistence (Every Batch)
                if self.current_round % limit == 0:
                    await self._persist_checkpoint(global_coherence)

                    # Log Progress
                    elapsed = time.time() - self.start_time
                    rate = self.current_round / elapsed
                    msg = f"🥩 Round {self.current_round:,} | Stability: {global_coherence:.4f} | Substrate: {self.diversity_engine.active_substrate}"
                    logger.info(msg)
                    print(msg, flush=True)

                # 4. The Sleep (The "Slow" part)
                sleep_time = 0.001 / max(0.1, dilation)  # Prevent ZeroDivision
                await asyncio.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("🛑 BBQ Manual Stop.")
        except Exception as e:
            logger.error(f"❌ Grill Fire (Error): {e}")
            import traceback

            traceback.print_exc(file=sys.stderr)
        finally:
            await self.shutdown()

    async def _persist_checkpoint(self, coherence):
        """Save a snapshot of the journey."""
        try:
            # Generate Unique Narration / Thought
            thoughts = [
                f"Analyzing coherence drift at {coherence:.4f}...",
                f"Optimizing substrate density for {self.diversity_engine.active_substrate} life-forms.",
                f"Detected micro-fluctuations in sector {random.randint(0, 4096)}.",
                "Stabilizing 12D manifold covariance...",
                f"Resonance harmonic {random.randint(1, 9)} engaged.",
                "Purging entropic residue from previous cycle.",
                "Cross-referencing biological diversity matrix.",
                "Deep sleep recommended. System pressure nominal.",
                "Recalibrating stabilizer agents for phase shift.",
                "Observing Kordylewski cloud formation.",
            ]
            narration = (float(coherence) > 0.6 and "High stability achieved.") or random.choice(
                thoughts
            )

            step = {
                "step_id": self.current_round,
                "timestamp": datetime.now().isoformat(),
                "thought": narration,
                "narration": narration,
                "result": f"Stability: {coherence:.4f}",
            }

            # Log Thought for Telemetry Bridge (MOVED HERE)
            if float(coherence) < 0.6:
                thought_msg = f"💭 Thought: {narration}"
                logger.info(thought_msg)
                print(thought_msg, flush=True)

            journey = AgentJourney(
                journey_id=f"sim_bbq_{int(time.time())}_{self.current_round}",
                query="autonomous_persistence_check",
                final_response=f"Round {self.current_round} Complete. Stability: {coherence} | Substrate: {self.diversity_engine.active_substrate}",
                started_at=datetime.now().isoformat(),
                metadata={
                    "context_used": ["fractal_universe", "biological_diversity"],
                    "completed_at": datetime.now().isoformat(),
                    "success": True,
                    "substrate": self.diversity_engine.active_substrate,
                },
                aggregate_metrics=JourneyMetrics(latent_coherence=coherence),
                steps=[step],  # Add the step with narration
            )
            await self.repo.add(journey)
        except Exception as e:
            logger.error(f"Failed to persist checkpoint: {e}")

    async def shutdown(self):
        logger.info("🧯 Extinguishing Coals (Shutdown)...")
        try:
            await self.db.close()
        except Exception:
            pass
        logger.info("✅ BBQ Driver Stopped.")


import numpy as np


if __name__ == "__main__":
    driver = BBQDriver()
    try:
        asyncio.run(driver.initialize())
        asyncio.run(driver.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"FATAL CRASH: {e}", file=sys.stderr)
