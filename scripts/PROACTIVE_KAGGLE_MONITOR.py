#!/usr/bin/env python3
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ProactiveMonitor")


class KaggleProactiveMonitor:
    def __init__(self):
        self.api = KaggleApi()
        self.api.authenticate()
        self.log_file = Path(".gemini_security/monitor_status.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.last_status = {}

    def check_submissions(self, competition_id):
        try:
            subs = self.api.competition_submissions(competition_id)
            if not subs:
                return

            latest = subs[0]
            status = str(latest.status)
            score = latest.publicScore

            key = f"sub_{competition_id}"
            if self.last_status.get(key) != status:
                logger.info(
                    f"🔔 SUBMISSION CHANGE: {competition_id} | Status: {status} | Score: {score}"
                )
                self.log_event("submission", competition_id, status, score)
                self.last_status[key] = status
        except Exception as e:
            logger.error(f"Error checking submissions for {competition_id}: {e}")

    def check_kernel(self, kernel_id):
        try:
            status_data = self.api.kernel_status(kernel_id)
            status = status_data.get("status")

            key = f"kernel_{kernel_id}"
            if self.last_status.get(key) != status:
                logger.info(f"🔔 KERNEL CHANGE: {kernel_id} | Status: {status}")
                self.log_event("kernel", kernel_id, status)
                self.last_status[key] = status
        except Exception as e:
            logger.error(f"Error checking kernel {kernel_id}: {e}")

    def log_event(self, type, identifier, status, score=None):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": type,
            "id": identifier,
            "status": status,
            "score": score,
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def run(self, interval=300):
        logger.info("🚀 Starting Proactive Kaggle Monitor...")
        competitions = ["ai-mathematical-olympiad-progress-prize-3", "arc-prize-2026-arc-agi-3"]
        kernels = [
            "manderson240/nemotron-lora-baseline-improved-manderson240",
            "manderson240/birdclef-2026-pytorch-baseline",
            "manderson240/measuring-progress-toward-agi-cognitive-framework",
        ]

        while True:
            for comp in competitions:
                self.check_submissions(comp)
            for kernel in kernels:
                self.check_kernel(kernel)

            time.sleep(interval)


if __name__ == "__main__":
    monitor = KaggleProactiveMonitor()
    monitor.run()
