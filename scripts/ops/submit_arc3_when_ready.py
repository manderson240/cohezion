#!/usr/bin/env python3
"""Automated submitter for ARC-AGI-3 ($850k Track).

Monitors manderson240/cohezion-arc-agi-3-autoharness-solver (v10).
Once KernelWorkerStatus.COMPLETE is reached, automatically submits submission.parquet via Kaggle CLI.
"""

import subprocess
import time
import sys

KERNEL = "manderson240/cohezion-arc-agi-3-autoharness-solver"
VERSION = "15"
COMP = "arc-prize-2026-arc-agi-3"
FILE = "submission.parquet"
MSG = "Cohezion v15: Directed Affordance Rarity SearchAgent (Avatar Tracking + Inverse Rarity Pathing + BBox Jitter)"

print(f"Monitoring {KERNEL} for completion...")

for attempt in range(120):  # Poll every 10s for up to 20 minutes
    res = subprocess.run(
        ["uv", "run", "kaggle", "kernels", "status", KERNEL],
        capture_output=True,
        text=True,
        check=False
    )
    status_text = res.stdout + res.stderr
    print(f"[{attempt * 10}s] Status: {status_text.strip()}")

    if "KernelWorkerStatus.COMPLETE" in status_text:
        print("Kernel execution COMPLETE! Submitting to competition...")
        sub_res = subprocess.run(
            [
                "uv", "run", "kaggle", "competitions", "submit",
                "-c", COMP,
                "-k", KERNEL,
                "-v", VERSION,
                "-f", FILE,
                "-m", MSG
            ],
            capture_output=True,
            text=True,
            check=False
        )
        print("Submission stdout:", sub_res.stdout)
        print("Submission stderr:", sub_res.stderr)
        if sub_res.returncode == 0:
            print("✓ Successfully submitted to ARC-AGI-3!")
        else:
            print(f"Submission exited with code {sub_res.returncode}")
        break
    elif "KernelWorkerStatus.ERROR" in status_text:
        print("❌ Kernel failed with ERROR.")
        break

    time.sleep(10)
