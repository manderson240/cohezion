import glob
import logging
import os
import time
from pathlib import Path


# Project OMEGA: Skill Crystallizer Watcher
# Responsibility: Watch for "MISSION SUCCESS" in logs/archive/ and queue them for crystallization.

LOG_DIRS = ["logs/archive/"]
TARGET_PHRASE = "MISSION SUCCESS"
POLL_INTERVAL = 60
QUEUE_DIR = Path(".agent/omega_queue")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - OMEGA - %(message)s",
    filename="logs/omega_watcher.log",
)


def scan_logs():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    processed_files = set()

    # Load processed state if exists (simple implementation)
    # real impl would use a db or state file

    logging.info("Starting Scan Cycle...")

    for log_dir in LOG_DIRS:
        files = glob.glob(os.path.join(log_dir, "*.log"))
        for file_path in files:
            if file_path in processed_files:
                continue

            try:
                with open(file_path, errors="ignore") as f:
                    content = f.read()
                    if TARGET_PHRASE in content:
                        logging.info(f"SUCCESS DETECTED in {file_path}")
                        # Create a trigger file in queue
                        basename = os.path.basename(file_path)
                        trigger_path = QUEUE_DIR / f"{basename}.crystallize"
                        if not trigger_path.exists():
                            with open(trigger_path, "w") as tf:
                                tf.write(f"SOURCE={os.path.abspath(file_path)}\nDETECTED={time.time()}")
                            logging.info(f"Queued {basename} for crystallization.")
            except Exception as e:
                logging.error(f"Error reading {file_path}: {e}")


def watch():
    print(f"--- Project OMEGA Watcher Started (PID: {os.getpid()}) ---")
    print(f"Monitoring {LOG_DIRS} for '{TARGET_PHRASE}'")

    while True:
        scan_logs()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    watch()
