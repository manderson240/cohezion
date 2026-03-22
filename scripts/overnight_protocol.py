"""
Overnight Protocol: Recovery -> Integrity -> Evolution
======================================================
1. Monitors the DB Ingestion of the 25M dataset.
2. Verifies integrity (Count check).
3. Archives the raw files (Failsafe).
4. Launches the 50M Next-Gen Simulation.
"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [OVERNIGHT] - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("overnight_protocol.log"), logging.StreamHandler()],
)
logger = logging.getLogger("OvernightOrchestrator")

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
TARGET_COUNT = 25_000_000
CHECK_INTERVAL = 60  # seconds


async def wait_for_ingestion():
    client = SurrealClient()
    await client.connect()

    logger.info("⏳ Monitoring Database Ingestion...")

    start_time = time.time()
    last_count = 0
    stalled_cycles = 0

    while True:
        try:
            # Check count
            res = await client.query("SELECT count() FROM universe_nodes GROUP ALL")

            # Parse result
            count = 0
            if isinstance(res, list) and res:
                item = res[0]
                results = item.get("result", []) if isinstance(item, dict) else item
                if results:
                    count = results[0].get("count", 0)

            int(time.time() - start_time)
            rate = (count - last_count) / CHECK_INTERVAL if last_count > 0 else 0

            logger.info(f"   - DB Count: {count:,} / {TARGET_COUNT:,} (Rate: {rate:.1f} rec/s)")

            if count >= TARGET_COUNT:
                logger.info("✅ Target count reached!")
                break

            # Stalls check
            if count == last_count and count > 0:
                stalled_cycles += 1
                if stalled_cycles > 10:  # 10 minutes no change
                    logger.warning("⚠️ Ingestion appears stalled. Proceeding with available data.")
                    break
            else:
                stalled_cycles = 0

            last_count = count

        except Exception as e:
            logger.error(f"Error checking DB: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

    await client.close()


def archive_failsafes():
    logger.info("📦 Archiving recovered data to cold storage...")
    try:
        # Tar the recovered files
        subprocess.run(
            [
                "tar",
                "-czf",
                "data/backup_recovered_sims.tar.gz",
                "data/restored_simulations",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
        logger.info("✅ Archive complete: data/backup_recovered_sims.tar.gz")
    except Exception as e:
        logger.error(f"❌ Archiving failed: {e}")


def launch_next_gen():
    logger.info("🚀 Launching 50M Next-Gen Simulation (FractalNexus)...")
    try:
        # Launch independently
        with open("fractal_nexus.log", "w") as out:
            subprocess.Popen(
                ["uv", "run", "python3", "scripts/fractal_nexus_mission.py"],
                cwd=REPO_ROOT,
                stdout=out,
                stderr=out,
                start_new_session=True,
            )
        logger.info("✅ Mission Launched. See fractal_nexus.log")
    except Exception as e:
        logger.error(f"❌ Mission Launch Failed: {e}")


async def main():
    logger.info("🌙 Starting Overnight Protocol")

    # 1. Wait for Data
    await wait_for_ingestion()

    # 2. Archive
    archive_failsafes()

    # 3. Launch
    launch_next_gen()

    logger.info("😴 Overlay Protocol Complete. System is autonomous.")


if __name__ == "__main__":
    asyncio.run(main())
