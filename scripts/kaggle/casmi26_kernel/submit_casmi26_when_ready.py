#!/usr/bin/env python3
"""Monitors manderson240/casmi26-analog-baseline-fork-cohezion and submits to CASMI26 upon completion."""

from pathlib import Path
import json
import subprocess
import sys
import time

KERNEL_REF = "manderson240/casmi26-analog-baseline-fork-cohezion"
COMP_ID = "enveda-CASMI26-molecule-id-mass-spectra"
SUB_FILE = "submission.csv"

KAGGLE_BIN = "/home/mike-anderson/.local/bin/kaggle" if Path("/home/mike-anderson/.local/bin/kaggle").exists() else "/home/mike-anderson/.local/share/uv/tools/kaggle/bin/kaggle"

TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 10
print(f"Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...", flush=True)

for attempt in range(1080):  # poll for up to 180 minutes (every 10s)
    res = subprocess.run([KAGGLE_BIN, "kernels", "status", KERNEL_REF], capture_output=True, text=True)
    status_str = res.stdout.strip()
    if attempt % 6 == 0 or "COMPLETE" in status_str:
        print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✓ Kernel run completed! Submitting v{TARGET_VERSION} to CASMI26...", flush=True)
        sub_msg = (
            f"Cohezion CASMI26 SOTA v{TARGET_VERSION}: Tautomer-Aware Canonical InChIKey14 Deduplication + "
            f"In-Silico Isomer Bond Cleavage Reranking (Target >0.350 MRR)"
        )
        submit_cmd = [
            sys.executable, str(Path(__file__).resolve().parent.parent / "kaggle_submit.py"),
            "auto",
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
