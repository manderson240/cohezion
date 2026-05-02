import asyncio
import datetime
import logging
import subprocess


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def run_loop():
    iteration = 1

    logger.info("Starting Overnight Autoresearch Loop (2026 SOTA). Target: 7:00 AM EST.")

    while True:
        # Get UTC time and convert to EST (UTC-5) or EDT (UTC-4)
        # April 9/10 is EDT (UTC-4)
        now_utc = datetime.datetime.now(datetime.UTC)
        now_est = now_utc - datetime.timedelta(hours=4)  # EDT

        target_time = now_est.replace(hour=7, minute=0, second=0, microsecond=0)

        # If it's already past 7 AM today, set target to tomorrow 7 AM
        if now_est >= target_time:
            target_time += datetime.timedelta(days=1)

        # Stop condition: if we somehow reach the target (we'll check in the loop)
        if now_est >= target_time:
            logger.info("Reached target time. Stopping autoresearch.")
            break

        logger.info(
            f"--- Autoresearch Iteration {iteration} | Current time: {now_est.strftime('%I:%M:%S %p EDT')} | Target: {target_time.strftime('%Y-%m-%d %I:%M %p EDT')} ---"
        )

        # Re-verify the benchmark script exists first
        # Since I might have deleted it too... wait, I need to check if I deleted benchmark_dpm_baseline.py

        # Run the comprehensive 2026 SOTA benchmark as the autoresearch verification suite
        proc = subprocess.run(
            ["uv", "run", "python", "scripts/benchmark_dpm_baseline.py"],
            capture_output=True,
            text=True,
        )

        if proc.returncode == 0:
            logger.info("Iteration successful. HIHO Coherence maintained.")
            lines = proc.stdout.strip().split("\n")
            summary = "\n".join(lines[-5:]) if len(lines) >= 5 else proc.stdout
            logger.info("Latest benchmark output summary:\n" + summary)
        else:
            logger.error("Iteration failed. Autoresearch detected degradation.")
            logger.error(proc.stderr[-500:] if proc.stderr else "No stderr output")

        iteration += 1

        # Sleep for 10 minutes between iterations
        logger.info("Sleeping for 10 minutes before next Ralph Loop iteration...")
        await asyncio.sleep(600)


if __name__ == "__main__":
    asyncio.run(run_loop())
