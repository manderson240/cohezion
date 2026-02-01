"""
Bandwidth Monitor for Alternative Self-Funding.

Simulates passive income from internet bandwidth sharing (e.g., Grass, Honeygain).
Monitors throughput and credits the SwarmPool based on usage.
"""

import asyncio
import logging
import random
import time

from cohezion.core.credit_manager import get_credit_manager
from cohezion.core.time_keeper import get_time_keeper

logger = logging.getLogger(__name__)

# Credits earned per MB of simulated data shared
CREDITS_PER_MB = 0.05


class BandwidthMonitor:
    """
    Simulates earning credits by sharing bandwidth.
    """

    def __init__(self):
        self.cm = get_credit_manager()
        self.tk = get_time_keeper()
        self._running = False
        self._metrics = {"mb_shared": 0.0, "credits_earned": 0.0, "uptime_seconds": 0}

    async def start(self, duration_seconds: int = 60):
        """
        Start the bandwidth sharing simulation.
        """
        self._running = True
        start_time = time.time()
        logger.info("BandwidthMonitor: Starting passive sharing stream...")

        while self._running and (time.time() - start_time) < duration_seconds:
            # Simulate random bandwidth usage (0.1 to 2.0 MB per burst)
            mb_burst = random.uniform(0.1, 2.0)
            credits = mb_burst * CREDITS_PER_MB

            self._metrics["mb_shared"] += mb_burst
            self._metrics["credits_earned"] += credits
            self._metrics["uptime_seconds"] = int(time.time() - start_time)

            # Credit the SwarmPool
            self.cm.credit(
                "SwarmPool", int(credits)
            ) if credits >= 1 else None  # Only credit whole units if simulated
            # For simulation, we'll allow fractional tracking if the manager supported it,
            # but for now we'll just log and batch.

            if self._metrics["credits_earned"] >= 1.0:
                batch_credits = int(self._metrics["credits_earned"])
                self.cm.credit("SwarmPool", batch_credits)
                self._metrics["credits_earned"] -= batch_credits

                await self.tk.log_event(
                    "BandwidthMonitor",
                    "BANDWIDTH_CREDIT",
                    {
                        "mb_shared": round(self._metrics["mb_shared"], 2),
                        "credits": batch_credits,
                    },
                )

            await asyncio.sleep(2)  # Sharing happens in bursts

        logger.info(f"BandwidthMonitor: Session complete. Metrics: {self._metrics}")
        return self._metrics

    def stop(self):
        self._running = False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    monitor = BandwidthMonitor()
    asyncio.run(monitor.start(10))
