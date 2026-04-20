import asyncio
import contextlib
import logging
import signal

from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.engineering.test_mycelium import TestMycelium
from cohezion.reliability.monitor import ResourceMonitor


logger = logging.getLogger("TestMyceliumDriver")


async def run_mycelium_loop():
    logger.info("🍄 Test Mycelium Driver starting...")
    client = SurrealClient()
    monitor = ResourceMonitor()
    mycelium = TestMycelium(client)

    # Ensure client is connected
    await client.connect()

    try:
        while True:
            vitals = monitor.get_vitals()
            # Stability Guardian Check: Only run if system is healthy
            if vitals["memory_percent"] > 90 or vitals.get("vram_percent", 0) > 90:
                logger.warning("⚠️ System pressure detected. Mycelium dormant.")
                await asyncio.sleep(60)
                continue

            logger.info("🍄 Mycelium: Checking for new trajectories...")
            await mycelium.run_cycle()

            # Wait 5 minutes between cycles
            await asyncio.sleep(300)
    except asyncio.CancelledError:
        logger.info("🍄 Mycelium Driver shutting down.")
    finally:
        await client.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    loop = asyncio.get_event_loop()
    main_task = loop.create_task(run_mycelium_loop())

    # Handle termination
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, main_task.cancel)

    with contextlib.suppress(asyncio.CancelledError):
        loop.run_until_complete(main_task)
