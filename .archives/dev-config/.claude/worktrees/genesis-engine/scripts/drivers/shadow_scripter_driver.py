import asyncio
import logging

# Path injection
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).parent.parent.parent))

from cohezion.engineering.shadow_scripter import ShadowScripter

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/shadow_scripter.log"), logging.StreamHandler()],
)
logger = logging.getLogger("ShadowDriver")


async def main():
    logger.info("🌑 Shadow Scripter Driver: Initializing...")

    db = SurrealClient()
    connected = await db.connect()
    if not connected:
        logger.error("❌ Failed to connect to SurrealDB. Shadow Scripter requires persistence.")
        return

    scripter = ShadowScripter(db_client=db)

    while True:
        try:
            logger.info("🌀 Starting new Shadow Cycle...")
            # Generate 3 trajectories per cycle to keep it "Low Power"
            await scripter.run_cycle(limit=3)
            logger.info("✨ Shadow Cycle complete.")
        except Exception as e:
            logger.error(f"Shadow Cycle failed: {e}", exc_info=True)

        # Every 6 hours
        logger.info("⌛ Sleeping for 6 hours...")
        await asyncio.sleep(6 * 3600)


if __name__ == "__main__":
    asyncio.run(main())
