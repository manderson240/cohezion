#!/usr/bin/env python3
"""Monitors manderson240/cohezion-biohub-v6 and submits to Biohub 3D Cell Tracking upon completion.

Uses Kaggle CLI via subprocess to ensure full compatibility.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("biohub_submit_daemon")

KERNEL_REF = "manderson240/cohezion-biohub-v6"
COMP_ID = "biohub-cell-tracking-during-development"
SUB_FILE = "submission.csv"
TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 25

KAGGLE_BIN = shutil.which("kaggle") or "/home/mike-anderson/.local/share/uv/tools/kaggle/bin/kaggle"


def log_to_surrealdb(status: str, version: int, message: str) -> None:
    sql = f"""
USE NS cohezion DB main;
UPSERT submission_record:biohub_v{version} CONTENT {{
    competition: '{COMP_ID}',
    kernel: '{KERNEL_REF}',
    kernel_version: {version},
    status: '{status}',
    submitted_at: time::now(),
    message: '{message}'
}};
"""
    req = urllib.request.Request(
        "http://localhost:8001/sql",
        data=sql.encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    auth = base64.b64encode(b"root:root").decode("ascii")
    req.add_header("Authorization", f"Basic {auth}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Submission logged to SurrealDB successfully.")
    except Exception as exc:
        logger.warning("Failed to log to SurrealDB: %s", exc)


def get_kernel_status() -> str:
    res = subprocess.run(
        [KAGGLE_BIN, "kernels", "status", KERNEL_REF],
        capture_output=True,
        text=True,
    )
    return res.stdout.strip()


def submit_kernel(version: int) -> bool:
    desc = (
        f"Cohezion Biohub V{version} SOTA: 0.946 Chassis + Guarded Heading Gap-Filling + "
        f"Collision Veto + IEEE-FP32 on NvidiaTeslaT4 (LB target 0.952-0.966+)"
    )
    cmd = [
        KAGGLE_BIN, "competitions", "submit",
        "-c", COMP_ID,
        "-k", KERNEL_REF,
        "-f", SUB_FILE,
        "-v", str(version),
        "-m", desc,
    ]
    logger.info("Submitting via Kaggle CLI: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = (res.stdout + " " + res.stderr).strip()
    logger.info("Submit response: %s", out)
    if "remaining today" in out or "Successfully submitted" in out or res.returncode == 0:
        log_to_surrealdb("SUBMITTED", version, desc)
        return True
    log_to_surrealdb("FAILED", version, out)
    return False


def main() -> None:
    logger.info("Monitoring kernel %s for version %d (using %s)...", KERNEL_REF, TARGET_VERSION, KAGGLE_BIN)

    for attempt in range(720):  # poll every 15s for up to 180 minutes
        status_output = get_kernel_status()
        logger.info("[%3d] Status output: %s", attempt, status_output)

        # Grace period for first 4 attempts (60s) to allow Kaggle backend to register new queued worker
        if attempt < 4 and ("ERROR" in status_output or "COMPLETE" in status_output):
            logger.info("Waiting for new version to register (stale previous status: %s)...", status_output)
            time.sleep(15)
            continue

        if "COMPLETE" in status_output:
            logger.info("✔ Kernel run completed! Automatically submitting v%d to %s...", TARGET_VERSION, COMP_ID)
            success = submit_kernel(TARGET_VERSION)
            if success:
                logger.info("✔ Successfully submitted v%d to %s!", TARGET_VERSION, COMP_ID)
                sys.exit(0)
            else:
                logger.error("Submission failed.")
                sys.exit(1)
        elif "ERROR" in status_output or "CANCELLED" in status_output:
            logger.error("Kernel terminated with error: %s", status_output)
            log_to_surrealdb("KERNEL_ERROR", TARGET_VERSION, status_output)
            sys.exit(1)

        time.sleep(15)

    logger.error("Timed out waiting for kernel completion.")
    sys.exit(2)


if __name__ == "__main__":
    main()
