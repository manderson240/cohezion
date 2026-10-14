#!/usr/bin/env python3
"""Autonomous Sentinel for Biohub & Kaggriculture.

Runs during unattended execution periods (1-3 hours):
1. Monitors Biohub v10 submission (Ref #56521849).
   - When complete, records public score.
   - If score is under 0.968, automatically updates kernel-metadata, pushes Biohub v11
     (cohezion-biohub-v11.ipynb), and launches submit_biohub_when_ready.py for v11!
2. Monitors Kaggriculture Ref #56522906 live rating as it climbs the tournament ladder.
3. Zero local memory footprint (<10MB RSS), safe for concurrent host processes.
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

LOG_FILE = Path("/tmp/kaggle_autonomous_sentinel.log")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("sentinel")

BIOHUB_COMP = "biohub-cell-tracking-during-development"
KAGGRICULTURE_COMP = "kaggriculture"
RSNA_COMP = "rsna-knee-abnormality-detection"
V10_REF = "56521849"
KAGG_REF = "56522906"
RSNA_REF = "56528465"
V11_DEPLOYED = False


def check_biohub():
    global V11_DEPLOYED
    try:
        res = subprocess.run(
            ["kaggle", "competitions", "submissions", "-c", BIOHUB_COMP],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in res.stdout.splitlines():
            if V10_REF in line:
                parts = line.split()
                # Find status and publicScore
                if "SubmissionStatus.COMPLETE" in line:
                    score = parts[-2] if len(parts) >= 2 else "UNKNOWN"
                    logger.info("🎉 Biohub v10 COMPLETED! Final Public Score: %s", score)
                    Path("/tmp/biohub_v10_score.json").write_text(
                        json.dumps({"ref": V10_REF, "score": score, "time": time.ctime()})
                    )
                    # If score < 0.968 and v11 not yet deployed, deploy v11
                    try:
                        score_float = float(score)
                    except ValueError:
                        score_float = 0.0

                    if score_float < 0.968 and not V11_DEPLOYED:
                        logger.info("Score %f below 0.968 target. Automatically pushing Biohub v11 SOTA...", score_float)
                        v11_nb = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v11.ipynb")
                        target_nb = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
                        if v11_nb.exists():
                            import shutil
                            shutil.copyfile(v11_nb, target_nb)
                            push_res = subprocess.run(
                                ["kaggle", "kernels", "push", "-p", "scripts/kaggle/biohub_v6/"],
                                capture_output=True,
                                text=True,
                                timeout=60,
                            )
                            logger.info("Pushed Biohub v11 kernel to Kaggle: %s", push_res.stdout.strip())
                            V11_DEPLOYED = True
                            # Start submit watcher in background
                            subprocess.Popen(
                                [sys.executable, "scripts/kaggle/biohub_v6/submit_biohub_when_ready.py", "11"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            logger.info("Launched submit_biohub_when_ready.py for v11.")
                    return True
                elif "SubmissionStatus.PENDING" in line:
                    logger.info("Biohub v10 (Ref #%s) still evaluating on 3D test set...", V10_REF)
                    return False
    except Exception as e:
        logger.warning("Error checking Biohub status: %s", e)
    return False


def check_kaggriculture():
    try:
        res = subprocess.run(
            ["kaggle", "competitions", "submissions", "-c", KAGGRICULTURE_COMP],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in res.stdout.splitlines():
            if KAGG_REF in line:
                parts = line.split()
                status = parts[-3] if len(parts) >= 3 else "UNKNOWN"
                score = parts[-2] if len(parts) >= 2 else "UNKNOWN"
                logger.info("Kaggriculture SOTA Frontier (Ref #%s): Status=%s, Rating=%s", KAGG_REF, status, score)
                break
    except Exception as e:
        logger.warning("Error checking Kaggriculture status: %s", e)


def check_rsna():
    try:
        res = subprocess.run(
            ["kaggle", "competitions", "submissions", "-c", RSNA_COMP],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in res.stdout.splitlines():
            if RSNA_REF in line:
                parts = line.split()
                if "SubmissionStatus.COMPLETE" in line:
                    score = parts[-2] if len(parts) >= 2 else "UNKNOWN"
                    logger.info("🎉 RSNA v12 COMPLETED! Final Public Score: %s", score)
                    Path("/tmp/rsna_v12_score.json").write_text(
                        json.dumps({"ref": RSNA_REF, "score": score, "time": time.ctime()})
                    )
                    return True
                elif "SubmissionStatus.PENDING" in line:
                    logger.info("RSNA v12 (Ref #%s) still evaluating on test set...", RSNA_REF)
                    return False
    except Exception as e:
        logger.warning("Error checking RSNA status: %s", e)
    return False


def main():
    logger.info("Starting Autonomous Sentinel for unattended monitoring (max 180 ticks / 3 hours)...")
    for tick in range(180):
        logger.info("--- Sentinel Tick %d/180 ---", tick + 1)
        check_biohub()
        check_kaggriculture()
        check_rsna()
        time.sleep(60)
    logger.info("Sentinel run completed after 3 hours.")


if __name__ == "__main__":
    main()
