#!/usr/bin/env python3
"""Monitors manderson240/cohezion-casmi26-fork-v4n-0421 and submits to CASMI26 upon completion."""

import subprocess
import sys
import time
from pathlib import Path

KERNEL_REF = "manderson240/cohezion-casmi26-fork-v4n-0421"
COMP_ID = "enveda-CASMI26-molecule-id-mass-spectra"
SUB_FILE = "submission.csv"

KAGGLE_BIN = "/home/mike-anderson/.local/bin/kaggle" if Path("/home/mike-anderson/.local/bin/kaggle").exists() else "/home/mike-anderson/.local/share/uv/tools/kaggle/bin/kaggle"

TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 4
print(f"Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...", flush=True)

for attempt in range(180):  # poll for up to 30 minutes (every 10s)
    res = subprocess.run([KAGGLE_BIN, "kernels", "status", KERNEL_REF], capture_output=True, text=True)
    status_str = res.stdout.strip()
    if attempt % 6 == 0 or "COMPLETE" in status_str:
        print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✓ Kernel run completed! Submitting v{TARGET_VERSION} to CASMI26...", flush=True)
        sub_msg = (
            f"Cohezion CASMI26 Podium v19: Restored POP_MU 0.25 (0.421 SOTA) + Adduct Surrogate + MetFrag Parsimony + FILL_25"
        )
        submit_cmd = [
            sys.executable, str(Path(__file__).resolve().parent.parent / "kaggle_submit.py"),
            "notebook",
            "-c", COMP_ID,
            "-k", KERNEL_REF,
            "-v", str(TARGET_VERSION),
            "-f", SUB_FILE,
            "-m", sub_msg,
            "-w",
        ]
        sub_res = subprocess.run(submit_cmd, capture_output=True, text=True)
        print("Submit output:", sub_res.stdout, sub_res.stderr, flush=True)
        sys.exit(0)
    elif "ERROR" in status_str or "CANCELLED" in status_str:
        print(f"Kernel terminated with status: {status_str}", flush=True)
        sys.exit(1)

    time.sleep(10)

print("Timed out waiting for kernel completion.", flush=True)
sys.exit(2)
