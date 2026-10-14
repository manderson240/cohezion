#!/usr/bin/env python3
"""Monitors manderson240/cohezion-arc-agi-3-autoharness-solver and submits to ARC-AGI-3 upon completion."""

from pathlib import Path
import json
import subprocess
import sys
import time

KERNEL_REF = "manderson240/cohezion-arc-agi-3-autoharness-solver"
COMP_ID = "arc-prize-2026-arc-agi-3"
SUB_FILE = "submission.parquet"

KAGGLE_BIN = "/home/mike-anderson/.local/bin/kaggle" if Path("/home/mike-anderson/.local/bin/kaggle").exists() else "/home/mike-anderson/.local/share/uv/tools/kaggle/bin/kaggle"

TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 3
print(f"Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...", flush=True)

for attempt in range(720):  # poll for up to 120 minutes
    res = subprocess.run([KAGGLE_BIN, "kernels", "status", KERNEL_REF], capture_output=True, text=True)
    status_str = res.stdout.strip()
    if attempt % 6 == 0 or "COMPLETE" in status_str:
        print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✓ Kernel run completed! Submitting v{TARGET_VERSION} to ARC-AGI-3...", flush=True)
        sub_msg = (
            f"Cohezion ARC-AGI-3 SOTA v27 (K-v{TARGET_VERSION}): Monadic Markov Anti-Cycle + "
            f"Vectorized 64-bit Zobrist Hashing (CPU Unlimited Quota)"
        )
        submit_cmd = [
            sys.executable,
            "scripts/kaggle/kaggle_submit.py",
            "notebook",
            "-c", COMP_ID,
            "-k", KERNEL_REF,
            "-v", str(TARGET_VERSION),
            "-f", SUB_FILE,
            "-m", sub_msg,
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
