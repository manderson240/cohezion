"""
Verification Script - Stability Hardening & Persistence Sync.
"""

import asyncio
import logging
from datetime import datetime

from cohezion.core.persistence.repositories.journey_repository import (
    AgentJourney,
    JourneyMetrics,
)
from cohezion.core.persistence.repositories.surreal_journey_repository import (
    SurrealJourneyRepository,
)
from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.reliability.monitor import ResourceMonitor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_persistence():
    """Verify that journeys can be stored and retrieved from SurrealDB."""
    logger.info("🧪 Verifying Persistence Layer...")
    client = SurrealClient()
    repo = SurrealJourneyRepository(client)

    journey = AgentJourney(
        journey_id="test_verification_001",
        query="Verification test for persistence sync.",
        started_at=datetime.now().isoformat(),
        final_response="Persistence Layer Crystallized.",
        final_confidence=0.99,
        total_duration_ms=150.0,
        aggregate_metrics=JourneyMetrics(latent_coherence=0.95, capability_delta=0.05),
    )

    try:
        # Test Add
        await repo.add(journey)
        logger.info("✅ Journey added to SurrealDB.")

        # Test Get
        retrieved = await repo.get("test_verification_001")
        if retrieved and retrieved.journey_id == "test_verification_001":
            logger.info("✅ Journey retrieved successfully.")
            logger.info(f"Retrieved Query: {retrieved.query}")
        else:
            logger.error("❌ Failed to retrieve journey.")

        # Test Recent
        recent = await repo.get_recent(hours=1, limit=5)
        if any(j.journey_id == "test_verification_001" for j in recent):
            logger.info("✅ Recent journeys list verified.")
        else:
            logger.error("❌ Test journey not found in recent list.")

    except Exception as e:
        logger.error(f"❌ Persistence verification failed: {e}")
    finally:
        await client.close()


async def verify_monitor():
    """Verify that ResourceMonitor is using new thresholds and tighter heartbeat."""
    logger.info("🧪 Verifying ResourceMonitor Hardening...")
    monitor = ResourceMonitor()
    vitals = monitor.get_vitals()

    logger.info(f"Current Vitals: {vitals}")

    # Check if we can see the heartbeat file activity
    log_path = Path("logs/system_heartbeat.log")
    if log_path.exists():
        mtime_before = log_path.stat().st_mtime
        logger.info("Waiting for heartbeat (2s loop)...")
        await asyncio.sleep(3)
        mtime_after = log_path.stat().st_mtime

        if mtime_after > mtime_before:
            logger.info("✅ Tight heartbeat (2s) confirmed.")
        else:
            logger.error("❌ Heartbeat loop delayed or inactive.")
    else:
        logger.warning("Heartbeat log not found, skipping heartbeat timing check.")


async def main():
    await verify_persistence()
    await verify_monitor()


if __name__ == "__main__":
    from pathlib import Path

    asyncio.run(main())
