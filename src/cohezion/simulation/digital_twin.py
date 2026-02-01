"""
Planetary Digital Twin: Data Ingestor
=====================================
Connects the internal simulation to external reality.
Ingests real-time data streams and converts them into "Entropy Signals"
that affect the Swarm's mood and coherence.

Signals:
1.  Finance (SNP500) -> Market Entropy
2.  Weather (Global Temp) -> Climate Entropy
"""

import logging
import random
import time
from collections.abc import Generator
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DigitalTwin")


@dataclass
class WorldState:
    timestamp: float
    market_entropy: float  # 0.0 (Stable) to 1.0 (Crash)
    climate_entropy: float  # 0.0 (Optimal) to 1.0 (Crisis)
    global_coherence: float  # Derived metric


class StreamIngestor:
    def __init__(self):
        self.running = False

    def connect(self):
        """Mock connection to External APIs (AlphaVantage, OpenWeatherMap)."""
        logger.info("🌍 Connecting to Planetary Sensor Grid...")
        time.sleep(1)
        logger.info("✅ Connection Established: [Finance, Climate, Energy]")
        self.running = True

    def stream(self) -> Generator[WorldState]:
        """Yields real-time world state updates."""
        while self.running:
            # Mock Data Generation
            # In production, this would await async API calls

            # 1. Market: Random Walk with Occasional Shocks
            market_shock = 0.8 if random.random() > 0.95 else 0.0
            market_entropy = random.uniform(0.1, 0.3) + market_shock

            # 2. Climate: Slow sinusoidal drift
            climate_entropy = 0.4 + (random.uniform(-0.05, 0.05))

            # 3. Calculate Global Coherence (Inverse of Entropy)
            avg_entropy = (market_entropy + climate_entropy) / 2
            coherence = 1.0 - avg_entropy

            state = WorldState(
                timestamp=time.time(),
                market_entropy=market_entropy,
                climate_entropy=climate_entropy,
                global_coherence=coherence,
            )

            logger.debug(f"Received World State: {state}")
            yield state

            time.sleep(1)  # 1Hz Update Rate

    def stop(self):
        self.running = False
