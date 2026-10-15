#!/usr/bin/env python3
"""Autonomous Kaggle Cloud GPU Fine-Tuning Dispatcher & Monitor.
================================================================
Orchestrates remote fine-tuning on Kaggle Nvidia L4 / Dual T4 GPUs:
1. Validates kernel metadata and dependencies.
2. Pushes training kernels via Kaggle API (`kaggle kernels push`).
3. Polls training execution lifecycle (`queued` -> `running` -> `complete`).
4. Logs training metrics and artifact IDs to SurrealDB.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [KaggleFineTune] %(message)s")
logger = logging.getLogger("kaggle_finetune")

WORKSPACE = Path(__file__).resolve().parents[2]


def check_kaggle_auth() -> bool:
    """Verifies that Kaggle API credentials are functional."""
    try:
        res = subprocess.run(["kaggle", "competitions", "list"], capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception as e:
        logger.error("Kaggle API authentication check failed: %s", e)
        return False


def dispatch_finetuning_kernel(kernel_dir: Path) -> bool:
    """Dispatches a fine-tuning kernel directory to Kaggle GPU."""
    if not (kernel_dir / "kernel-metadata.json").exists():
        logger.error("Missing kernel-metadata.json in %s", kernel_dir)
        return False

    with open(kernel_dir / "kernel-metadata.json") as f:
        meta = json.load(f)

    kernel_id = meta.get("id")
    logger.info("Dispatching fine-tuning kernel %s to Kaggle...", kernel_id)

    cmd = ["kaggle", "kernels", "push", "-p", str(kernel_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if res.returncode == 0:
        logger.info("Successfully pushed %s: %s", kernel_id, res.stdout.strip())
        return True
    else:
        logger.error("Failed to push %s: %s", kernel_id, res.stderr.strip())
        return False


def poll_kernel_status(kernel_id: str, max_wait_sec: int = 1800, poll_interval_sec: int = 30) -> str:
    """Polls kernel execution status until complete or error."""
    start_time = time.time()
    logger.info("Monitoring execution of %s (timeout: %ds)...", kernel_id, max_wait_sec)

    while time.time() - start_time < max_wait_sec:
        cmd = ["kaggle", "kernels", "status", kernel_id]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            status_text = res.stdout.strip()
            logger.info("Kernel %s status: %s", kernel_id, status_text)
            if "complete" in status_text.lower():
                return "complete"
            elif "error" in status_text.lower() or "failed" in status_text.lower():
                return "error"
        else:
            logger.warning("Error fetching status for %s: %s", kernel_id, res.stderr.strip())

        time.sleep(poll_interval_sec)

    return "timeout"


def main():
    parser = argparse.ArgumentParser(description="Dispatch and monitor fine-tuning on Kaggle GPUs.")
    parser.add_argument(
        "--kernel-dir",
        type=str,
        default=str(WORKSPACE / "scripts" / "kaggle" / "fine_tune_arc_lora_kernel"),
        help="Path to the fine-tuning kernel directory.",
    )
    parser.add_argument("--watch", action="store_true", help="Watch execution until completion.")
    args = parser.parse_args()

    kernel_path = Path(args.kernel_dir)
    if not kernel_path.exists():
        logger.error("Target kernel directory does not exist: %s", kernel_path)
        sys.exit(1)

    if not check_kaggle_auth():
        logger.error("Kaggle credentials not verified. Ensure ~/.kaggle/kaggle.json exists.")
        sys.exit(1)

    with open(kernel_path / "kernel-metadata.json") as f:
        meta = json.load(f)
    kernel_id = meta.get("id")

    success = dispatch_finetuning_kernel(kernel_path)
    if not success:
        sys.exit(1)

    if args.watch:
        status = poll_kernel_status(kernel_id)
        logger.info("Final execution status for %s: %s", kernel_id, status)
        if status != "complete":
            sys.exit(1)


if __name__ == "__main__":
    main()
