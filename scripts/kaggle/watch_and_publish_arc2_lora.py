#!/usr/bin/env python3
"""Autonomous Watcher & Auto-Publisher for ARC-AGI-2 LoRA Fine-Tuning.
====================================================================
1. Monitors Kaggle Cloud execution of `manderson240/cohezion-arc2-lora-finetune`.
2. Upon completion, downloads the fine-tuned adapter weights (`adapter_model.safetensors`).
3. Publishes a new version to Kaggle Models Hub (`manderson240/cohezion-arc2-lora-adapter`).
4. Updates offline submission metadata so tonight's midnight harvest uses the new weights.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [LoRAWatcher] %(message)s")
logger = logging.getLogger("arc2_lora_watcher")

KERNEL_SLUG = "manderson240/cohezion-arc2-lora-finetune"
MODEL_OWNER = "manderson240"
MODEL_SLUG = "cohezion-arc2-lora-adapter"
INSTANCE_SLUG = "transformers"
DOWNLOAD_DIR = Path("/tmp/arc_lora_v7_out")


def check_status() -> str:
    res = subprocess.run(["kaggle", "kernels", "status", KERNEL_SLUG], capture_output=True, text=True, timeout=20)
    if res.returncode == 0:
        return res.stdout.strip()
    return "UNKNOWN"


def publish_model_version(adapter_dir: Path) -> bool:
    logger.info("Preparing metadata for new Kaggle Model version...")
    metadata = {
        "ownerSlug": MODEL_OWNER,
        "modelSlug": MODEL_SLUG,
        "instanceSlug": INSTANCE_SLUG,
        "framework": "transformers",
        "overview": "Production-scale bfloat16 LoRA adapter (r=32, alpha=64, 1500 steps) fine-tuned on 5,000 synthetic reasoning tasks.",
        "usage": "# Model Format\nSafetensors LoRA adapter\n\n# Training Data\nARC-AGI-2 challenges + 5,000 Synthetic Reasoning Tasks\n",
        "licenseName": "Apache 2.0",
        "fineTunable": True,
        "trainingData": [],
        "modelInstanceType": "unspecified",
        "baseModelInstanceId": 0,
        "externalBaseModelUrl": ""
    }
    with open(adapter_dir / "model-instance-metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Publishing new model instance version to Kaggle Models Hub...")
    cmd = [
        "kaggle", "models", "instances", "versions", "create",
        "-p", str(adapter_dir),
        "-n", "Production Scale LoRA (r=32, 1500 steps, 5k tasks)"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    logger.info("Upload stdout: %s", res.stdout.strip())
    if res.stderr:
        logger.warning("Upload stderr: %s", res.stderr.strip())
    return res.returncode == 0


def main():
    logger.info("Starting autonomous watcher for %s...", KERNEL_SLUG)
    poll_interval = 60

    while True:
        status_line = check_status()
        logger.info("Status: %s", status_line)

        if "COMPLETE" in status_line:
            logger.info("Kernel execution COMPLETED! Downloading artifacts...")
            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            dl_res = subprocess.run(
                ["kaggle", "kernels", "output", KERNEL_SLUG, "-p", str(DOWNLOAD_DIR)],
                capture_output=True, text=True, timeout=120
            )
            logger.info("Download result: %s", dl_res.stdout.strip())

            # Find adapter directory
            adapter_path = DOWNLOAD_DIR / "cohezion_arc_lora_adapter"
            if not adapter_path.exists():
                candidates = list(DOWNLOAD_DIR.glob("**/adapter_model.safetensors"))
                if candidates:
                    adapter_path = candidates[0].parent

            if adapter_path and adapter_path.exists():
                logger.info("Found adapter directory at %s. Publishing to Models Hub...", adapter_path)
                success = publish_model_version(adapter_path)
                if success:
                    logger.info("✓ Model published to Kaggle Models Hub successfully!")
                else:
                    logger.error("Failed to publish model version to Kaggle Models Hub.")
            else:
                logger.error("Could not find adapter_model.safetensors in %s", DOWNLOAD_DIR)
            break

        elif "ERROR" in status_line or "FAILED" in status_line:
            logger.error("Kernel execution entered ERROR/FAILED state: %s", status_line)
            break

        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
