#!/usr/bin/env python3
"""Monitors manderson240/arc-agi-2-fork-lb33-89-20260903 and submits to ARC-AGI-2 competition upon completion."""

from pathlib import Path
import json
import subprocess
import sys
import time

KERNEL_REF = "manderson240/arc-agi-2-fork-lb33-89-20260903"
COMP_ID = "arc-prize-2026-arc-agi-2"
SUB_FILE = "submission.json"

KAGGLE_BIN = "/home/mike-anderson/.local/bin/kaggle" if Path("/home/mike-anderson/.local/bin/kaggle").exists() else "/home/mike-anderson/.local/share/uv/tools/kaggle/bin/kaggle"

TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 12
print(f"Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...", flush=True)

for attempt in range(1080):  # poll for up to 180 minutes (every 10s)
    res = subprocess.run([KAGGLE_BIN, "kernels", "status", KERNEL_REF], capture_output=True, text=True)
    status_str = res.stdout.strip()
    if attempt % 6 == 0 or "COMPLETE" in status_str:
        print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✓ Kernel run completed! Submitting v{TARGET_VERSION} to ARC-AGI-2...", flush=True)
        sub_msg = (
            f"Cohezion ARC-AGI-2 SOTA v{TARGET_VERSION}: Zero-False-Prune AutoHarness Invariants + "
            f"Qwen3-4B LoRA SFT139 on NvidiaL4"
        )
        submit_cmd = [
            KAGGLE_BIN, "competitions", "submit",
            "-c", COMP_ID,
            "-f", SUB_FILE,
            "-m", sub_msg,
            "-k", KERNEL_REF,
            "-v", str(TARGET_VERSION)
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
