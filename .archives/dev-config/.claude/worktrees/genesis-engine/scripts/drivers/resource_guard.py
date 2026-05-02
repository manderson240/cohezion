#!/usr/bin/env python3
"""
Resource Guard Daemon.

Runs in the background to prevent OOM events by monitoring system resources
and taking active measures (alerts, termination) when thresholds are crossed.
"""

import logging
import sys
import time
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parents[2] / "src"))

from cohezion.core.resource_monitor import ResourceMonitor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [GUARDIAN] - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/archive/resource_guard.log"),
    ],
)
logger = logging.getLogger("ResourceGuard")


def main():
    logger.info("🛡️ Resource Guard initialized. Monitoring 128GB System...")

    # Set thresholds: Warn at 85%, Kill at 92%
    monitor = ResourceMonitor(cpu_threshold=90.0, memory_threshold=92.0)

    try:
        while True:
            # 1. Report Health
            stats = monitor.get_stats()
            mem_pct = stats["memory_percent"]

            if mem_pct > 80.0:
                logger.warning(
                    f"Memory Pressure: {mem_pct:.1f}% used ({stats['used_memory_gb']:.1f}/{stats['total_memory_gb']:.1f} GB)"
                )

            # 2. Active Defense
            actions = monitor.check_and_enforce()
            for action in actions:
                logger.warning(f"⚔️ EFFECT: {action}")

            # 3. Heartbeat (Low frequency normally, high if stressed)
            sleep_time = 5 if mem_pct > 80 else 30
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Resource Guard stopping...")


if __name__ == "__main__":
    main()
