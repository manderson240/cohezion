#!/usr/bin/env python3
"""Monitors manderson240/cohezion-rsna-knee-sota-ensemble and submits to RSNA Knee competition upon completion."""

from pathlib import Path
import subprocess
import sys
import time

KERNEL_REF = "manderson240/cohezion-rsna-knee-sota-ensemble"
COMP_ID = "rsna-knee-abnormality-detection"
SUB_FILE = "submission.csv"

PYTHON_BIN = sys.executable
KAGGLE_BIN = ".venv/bin/kaggle"

TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 32
print(f"Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...", flush=True)

for attempt in range(1080):  # poll for up to 180 minutes (every 10s)
    res = subprocess.run([KAGGLE_BIN, "kernels", "status", KERNEL_REF], capture_output=True, text=True)
    status_str = res.stdout.strip()
    if attempt % 6 == 0 or "COMPLETE" in status_str:
        print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✓ Kernel run completed! Submitting v{TARGET_VERSION} to RSNA Knee Abnormality Detection...", flush=True)
        sub_msg = (
            f"Cohezion RSNA Knee SOTA v{TARGET_VERSION}: Restored Pure Copula Rank Alignment + "
            f"Strict Probability Clipping [1e-6, 1.0 - 1e-6] (NvidiaL4)"
        )
        submit_cmd = [
            PYTHON_BIN,
            "scripts/kaggle/kaggle_submit.py",
            "notebook",
            "-c", COMP_ID,
            "-k", KERNEL_REF,
            "-v", str(TARGET_VERSION),
            "-f", SUB_FILE,
            "-m", sub_msg,
            "--code-path", "scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb"
        ]
        sub_res = subprocess.run(submit_cmd, capture_output=True, text=True)
        print(sub_res.stdout, sub_res.stderr, flush=True)
        sys.exit(sub_res.returncode)
    elif "ERROR" in status_str or "CANCELLED" in status_str:
        print(f"Kernel terminated with status: {status_str}", flush=True)
        sys.exit(1)

    time.sleep(10)

print("Timed out waiting for kernel completion.", flush=True)
sys.exit(2)
