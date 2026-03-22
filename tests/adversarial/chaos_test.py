import logging
import sys
import time

import requests


# Configure "Red Team" Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [RED TEAM] - %(message)s")
logger = logging.getLogger("ChaosMonkey")

BASE_URL = "http://127.0.0.1:5000"


def inject_chaos():
    """Attack 1: Massive Entropy Injection."""
    logger.info("🔥 INJECTING CHAOS: Spiking System Entropy...")
    # We cheat and use the DEBUG/God-Mode endpoint (if it existed)
    # Since it doesn't, we simulate "External Stress" by flooding requests
    # and relying on the Simulation realizing it's under load?
    # Or better: We assume there's a back-door for testing.
    # For now, let's just monitor and assert it handles 'Natural' chaos if we can't force it.

    # Actually, let's hit a route that triggers high load
    try:
        # Trigger Chaos Mode
        requests.post(f"{BASE_URL}/chaos", timeout=1.0)
        logger.info("☠️ Chaos Payload Delivered.")
    except Exception as e:
        logger.error(f"Failed to inject chaos: {e}")


def monitor_recovery():
    """Polls state to measure MTTR (Mean Time To Recovery)."""
    start_time = time.time()
    spiked = False
    recovered = False

    logger.info("⏱️ Monitoring Recovery Protocol...")

    for step in range(30):  # Monitor for 30 ticks (approx 30s)
        try:
            response = requests.get(f"{BASE_URL}/state")
            data = response.json()
            entropy = data.get("avg_entropy", 0.0)
            corrections = data.get("corrections", 0)

            logger.info(f"Tick {step}: Entropy={entropy:.2f} (Corrections={corrections})")

            # 1. Wait for the Spike
            if not spiked:
                if entropy > 0.8:
                    logger.info("🔥 CHAOS CONFIRMED: Entropy Spike Detected!")
                    spiked = True
                    start_time = time.time()  # Start recovery timer now

            # 2. Wait for Recovery
            elif spiked and entropy < 0.3:
                logger.info(f"✅ SYSTEM RECOVERED in {time.time() - start_time:.2f}s!")
                recovered = True
                break

        except Exception as e:
            logger.warning(f"Connection glitch: {e}")

        time.sleep(1)

    if not spiked:
        logger.error("❌ FAILED: Chaos never manifested (No Spike).")
        sys.exit(1)

    if not recovered:
        logger.error("❌ FAILED: System did not stabilize in time.")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure Sim is running
    try:
        requests.get(f"{BASE_URL}/")
    except Exception:
        logger.error("Target DOWN. Start Diplomat first.")
        sys.exit(1)

    inject_chaos()
    monitor_recovery()
