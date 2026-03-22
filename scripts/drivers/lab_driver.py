"""
Lab Driver - Orchestrates the Autonomous AI Lab background execution.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path


# Add src to sys.path
sys.path.append(str(Path(__file__).parent / "src"))

from cohezion.swarm.agents.lab_agent import LabAgent


# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/lab_driver.log"), logging.StreamHandler()],
)
logger = logging.getLogger("LabDriver")

import contextlib

import psutil


async def get_throttle_delay(base_delay: float = 60.0) -> float:
    """Calculate delay based on system load to implement autonomic scaling."""
    cpu_usage = psutil.cpu_percent(interval=None)
    ram_usage = psutil.virtual_memory().percent

    # Scaling factor: if load is high, increase delay
    # Thresholds: > 70% CPU or > 80% RAM is "High Heat"
    if cpu_usage > 70 or ram_usage > 80:
        logger.warning(f"🔥 High load detected (CPU: {cpu_usage}%, RAM: {ram_usage}%). Throttling...")
        return base_delay * 3  # Triple the delay
    elif cpu_usage > 40 or ram_usage > 60:
        logger.info(f"🌤 Moderate load (CPU: {cpu_usage}%, RAM: {ram_usage}%). Slight throttle.")
        return base_delay * 1.5
    else:
        logger.info(f"❄ Low load (CPU: {cpu_usage}%, RAM: {ram_usage}%). Optimal scaling.")
        return base_delay


async def main():
    logger.info("🚀 Starting Autonomous AI Lab Driver with Autonomic Scaling...")

    lab_agent = LabAgent()

    # Handle termination signals
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def shutdown():
        logger.info("🛑 Shutdown signal received.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    cycle_count = 0
    last_report_time = time.time()
    last_maintenance_time = 0
    base_idle_delay = 60.0

    try:
        while not stop_event.is_set():
            cycle_count += 1
            logger.info(f"--- Cycle {cycle_count} ---")

            # 1. Resource Stewardship: Check pressure before starting
            cpu_usage = psutil.cpu_percent(interval=1)
            ram_usage = psutil.virtual_memory().percent
            if cpu_usage > 90 or ram_usage > 95:
                logger.warning(f"🚨 CRITICAL LOAD: CPU {cpu_usage}%, RAM {ram_usage}%. Skipping cycle.")
                await asyncio.sleep(300)  # Wait 5 mins
                continue

            # 2. Automated Module Maintenance (Every 4 hours)
            current_time = time.time()
            if current_time - last_maintenance_time >= 14400:
                logger.info("🛠 Running Automated Module Maintenance...")
                try:
                    # Run context verification
                    verify_process = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "tests/verify_context.py",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _stdout, stderr = await verify_process.communicate()
                    if verify_process.returncode == 0:
                        logger.info("✅ Context Integrity Verified.")
                    else:
                        logger.error(f"❌ Context Verification FAILED: {stderr.decode()}")
                except Exception as e:
                    logger.error(f"Maintenance Error: {e}")
                last_maintenance_time = current_time

            # 3. 0.5 HIHO Stability: Inject stability constraints into research
            # We wrap the cycle with a stability check
            logger.info("⚖ Applying 0.5 HIHO Stability Constraint...")

            # Run a research cycle
            await lab_agent.run_cycle()

            # 4. 30-Minute Status Report (User Request)
            if current_time - last_report_time >= 1800:
                logger.info("🕒 Sending 30-minute status report...")
                await lab_agent.send_summary_report()
                last_report_time = current_time

            # 5. Autonomic Scaling: Dynamic wait based on system load
            delay = await get_throttle_delay(base_idle_delay)
            logger.info(f"Waiting for {delay:.1f}s (Autonomic Scaling)...")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=delay)

    except Exception as e:
        logger.error(f"Lab Driver CRASHED: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up...")
        if cycle_count > 0:
            await lab_agent.send_summary_report()
        logger.info("Lab Driver Offline.")


if __name__ == "__main__":
    asyncio.run(main())
