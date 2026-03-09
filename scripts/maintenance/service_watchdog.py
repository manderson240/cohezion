import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

import logging
import time

from cohezion.system.daemon_manager import DaemonManager


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Watchdog")


def main():
    dm = DaemonManager()
    logger.info("🛡️ Cohezion Service Watchdog Started.")

    # Target components
    targets = ["surrealdb", "api", "simulation", "recorder"]

    try:
        while True:
            for component in targets:
                if not dm.is_running(dm.COMPONENTS[component]["cmd_signature"]):
                    logger.warning(f"⚠️ {component.upper()} is down! Restarting...")
                    dm.start_component(component)
                else:
                    # Optional: Port check for deeper health validation
                    pass

            # Check every 30 seconds - low overhead
            time.sleep(30)

    except KeyboardInterrupt:
        logger.info("Watchdog stopped by user.")
    except Exception as e:
        logger.error(f"Watchdog crashed: {e}")


if __name__ == "__main__":
    main()
