#!/usr/bin/env python3
"""
Nightly Job: FLUME VAE Continuous Learning
Ingests daily trajectory data and retrains the VAE to improve latent accuracy.
"""

import logging
import subprocess
from pathlib import Path


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
DATA_DIR = PROJECT_ROOT / "apps/dashboard/src/assets/data"
TRAIN_SCRIPT = PROJECT_ROOT / "scripts/train_flume.py"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VAERetrainer")


def main():
    logger.info("🌙 Starting Nightly VAE Retraining...")

    # 1. Sense: Gather day's trajectories
    pulses = list(DATA_DIR.glob("pulse_*.json"))
    if not pulses:
        logger.info("No new trajectories to train on.")
        return

    # 2. Distill: Pre-process into training format
    # In production, this would aggregate JSONs into a single .npy or .jsonl
    logger.info(f"Ingesting {len(pulses)} trajectory points...")

    # 3. Manifest: Execute retraining
    # Using the existing training driver
    cmd = f"uv run {TRAIN_SCRIPT} --epochs 5 --batch-size 32"
    logger.info(f"Executing: {cmd}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        logger.info("✅ VAE Retraining Successful. Model weights updated.")
    else:
        logger.error(f"❌ Retraining failed: {result.stderr}")


if __name__ == "__main__":
    main()
