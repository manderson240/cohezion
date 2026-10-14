#!/usr/bin/env python3
"""Automated submitter for Enveda CASMI26 Molecule ID.

Monitors manderson240/casmi26-analog-baseline-fork-cohezion (v8).
Once KernelWorkerStatus.COMPLETE is reached, automatically downloads output and submits submission.csv via Kaggle CLI.
"""

import os
import shutil
import subprocess
import sys
import time

KERNEL = "manderson240/casmi26-analog-baseline-fork-cohezion"
COMP = "enveda-CASMI26-molecule-id-mass-spectra"
OUTPUT_DIR = "/tmp/casmi26_v8_out"
MSG = "Cohezion CASMI26 SOTA v8: Variance-Penalized Stepped CE Fusion + Gaussian Adduct Gating + InChIKey14 Deduplication"

# Find kaggle binary
KAGGLE_BIN = shutil.which("kaggle") or "/home/mike-anderson/dev/cohezion/.venv/bin/kaggle"

print(f"Monitoring {KERNEL} for completion and automated submission (using {KAGGLE_BIN})...")

while True:
    res = subprocess.run(
        [KAGGLE_BIN, "kernels", "status", KERNEL],
        capture_output=True,
        text=True,
        check=False,
    )
    status_text = (res.stdout + res.stderr).strip()
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Kernel Status: {status_text}")

    if "KernelWorkerStatus.COMPLETE" in status_text:
        print("Kernel execution COMPLETE! Downloading output and submitting...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        dl_res = subprocess.run(
            [KAGGLE_BIN, "kernels", "output", KERNEL, "-p", OUTPUT_DIR],
            capture_output=True,
            text=True,
            check=False,
        )
        print("Download output:", dl_res.stdout.strip())

        sub_file = os.path.join(OUTPUT_DIR, "submission.csv")
        if os.path.exists(sub_file):
            sub_res = subprocess.run(
                [
                    KAGGLE_BIN,
                    "competitions",
                    "submit",
                    "-c",
                    COMP,
                    "-f",
                    sub_file,
                    "-m",
                    MSG,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            print("Submission stdout:", sub_res.stdout.strip())
            print("Submission stderr:", sub_res.stderr.strip())
            if sub_res.returncode == 0:
                print("✓ Successfully submitted v8 to Enveda CASMI26!")
                break
        else:
            print("submission.csv not found in downloaded output!")
            break

    elif "KernelWorkerStatus.ERROR" in status_text or "KernelWorkerStatus.CANCELLED" in status_text:
        print(f"Kernel failed with status: {status_text}")
        break

    time.sleep(60)
