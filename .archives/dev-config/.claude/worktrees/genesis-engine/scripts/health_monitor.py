import logging
import subprocess
import time
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("HealthMonitor")

REPO_ROOT = Path(__file__).parent.parent.resolve()
JANITOR_SCRIPT = REPO_ROOT / "scripts" / "repo_janitor.py"
CHECK_INTERVAL_SECONDS = 3600  # Hourly

from cohezion.healing import get_healing_system


def run_janitor():
    logger.info("🕒 Running scheduled repository health check...")
    try:
        # Check vitals first
        import sys

        sys.path.append(str(REPO_ROOT / "scripts"))
        import repo_janitor

        vitals = repo_janitor.check_git_vitals(use_cache=False)

        # Register with healing system
        healing = get_healing_system()
        status = healing.detector.check("repository", "bloat", vitals.get("pending_count", 0), 1000)

        if status.status != "healthy":
            logger.warning(f"⚠️ Repository degradation detected: {status.status}. Triggering autonomous cleanup.")
            subprocess.run(["python3", str(JANITOR_SCRIPT)], cwd=REPO_ROOT, check=True)

            # Database pruning
            logger.info("🧹 Performing autonomous database pruning...")
            subprocess.run(
                ["python3", str(REPO_ROOT / "scripts" / "db_pruning.py"), "7"],
                cwd=REPO_ROOT,
                check=True,
            )

            # Security Audit
            logger.info("🛡️ Performing autonomous security audit...")
            subprocess.run(
                ["python3", str(REPO_ROOT / "scripts" / "security_scout.py")],
                cwd=REPO_ROOT,
                check=True,
            )

            # Auto-checkpoint if on a task branch
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            if branch != "main" and branch != "master":
                logger.info(f"Autonomous checkpointing for branch: {branch}")
                subprocess.run(
                    [
                        "python3",
                        str(REPO_ROOT / "scripts" / "work_manager.py"),
                        "checkpoint",
                        "-m",
                        "Autonomic hygiene checkpoint",
                    ],
                    cwd=REPO_ROOT,
                )

        logger.info("✅ Health check complete.")
    except Exception as e:
        logger.error(f"❌ Autonomic action failed: {e}")


def monitor_loop():
    logger.info("🛡️ Cohezion Health Monitor started.")
    while True:
        run_janitor()
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        monitor_loop()
    except KeyboardInterrupt:
        logger.info("Stopping health monitor...")
