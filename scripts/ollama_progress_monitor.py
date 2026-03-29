#!/usr/bin/env python3
"""
Ollama Progress Monitor - Tracks the usage maximization progress
"""

import json
import logging
import time
from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/mike-anderson/dev/cohezion/logs/ollama_progress.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def find_latest_stats_file():
    """Find the most recent Ollama maximization stats file."""
    data_dir = Path("/home/mike-anderson/dev/cohezion/data")
    if not data_dir.exists():
        return None

    stats_files = list(data_dir.glob("ollama_maximization_*.json"))
    if not stats_files:
        return None

    # Return the most recently modified file
    return max(stats_files, key=lambda f: f.stat().st_mtime)


def load_stats(file_path):
    """Load stats from JSON file."""
    try:
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading stats from {file_path}: {e}")
        return None


def main():
    """Monitor Ollama maximization progress."""
    logger.info("Starting Ollama progress monitor")

    last_check = 0

    try:
        while True:
            # Find the latest stats file
            latest_file = find_latest_stats_file()

            if latest_file and latest_file.stat().st_mtime > last_check:
                # New or updated stats file
                stats = load_stats(latest_file)
                if stats:
                    logger.info("=== OLLAMA USAGE PROGRESS ===")
                    logger.info(f"File: {latest_file.name}")
                    logger.info(f"Duration: {stats.get('test_duration_hours', 0):.2f} hours")
                    logger.info(f"Total Requests: {stats.get('total_requests', 0)}")
                    logger.info(f"Success Rate: {stats.get('success_rate_percent', 0):.2f}%")
                    logger.info(f"Requests/Hour: {stats.get('requests_per_hour', 0):.2f}")

                    # Show top models used
                    models_used = stats.get("models_used", {})
                    if models_used:
                        sorted_models = sorted(
                            models_used.items(), key=lambda x: x[1], reverse=True
                        )
                        logger.info(f"Top Models Used: {dict(sorted_models[:3])}")

                    logger.info("=" * 40)

                last_check = latest_file.stat().st_mtime

            # Wait before checking again
            time.sleep(30)  # Check every 30 seconds

    except KeyboardInterrupt:
        logger.info("Progress monitor stopped by user")
    except Exception as e:
        logger.error(f"Progress monitor error: {e}")


if __name__ == "__main__":
    main()
