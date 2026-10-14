#!/usr/bin/env python3
"""Watch manderson240/cohezion-rsna-knee-0-957-r7-blend version 3 and submit to RSNA Knee upon completion."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("rsna_v33_submitter")

KERNEL_SLUG = "manderson240/cohezion-rsna-knee-0-957-r7-blend"
COMPETITION = "rsna-knee-abnormality-detection"
NOTEBOOK_PATH = "scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb"
TARGET_VERSION = 3


def main() -> None:
    api = KaggleApi()
    api.authenticate()

    logger.info("Watching kernel '%s' for version %d completion...", KERNEL_SLUG, TARGET_VERSION)

    start_time = time.time()
    last_status = None

    while (time.time() - start_time) < 3600:  # 60 minute max timeout
        status_res = api.kernels_status(KERNEL_SLUG)
        status = status_res.get("status") if isinstance(status_res, dict) else getattr(status_res, "status", str(status_res))

        if status != last_status:
            logger.info("Kernel execution status: %s", status)
            last_status = status

        if "COMPLETE" in str(status).upper():
            logger.info("✓ Kernel execution COMPLETE! Dispatching RSNA Knee SOTA v33 submission...")
            cmd = [
                sys.executable,
                "scripts/kaggle/kaggle_submit.py",
                "notebook",
                "-c", COMPETITION,
                "-k", KERNEL_SLUG,
                "-v", str(TARGET_VERSION),
                "-f", "submission.csv",
                "-m", "Cohezion RSNA Knee SOTA v33: Calibrated Tri-Model Multi-Resolution Blend (Raptor-384 + Raptor-224 + R7) + Per-Pathology Copula Weights",
                "--code-path", NOTEBOOK_PATH,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            logger.info("Submission Exit Code: %d", res.returncode)
            logger.info("Submission Stdout:\n%s", res.stdout)
            if res.stderr:
                logger.warning("Submission Stderr:\n%s", res.stderr)
            return

        elif "ERROR" in str(status).upper() or "CANCEL" in str(status).upper():
            logger.error("Kernel failed with status: %s", status)
            sys.exit(1)

        time.sleep(15)

    logger.error("Timed out waiting for kernel completion.")
    sys.exit(2)


if __name__ == "__main__":
    main()
