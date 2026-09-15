#!/usr/bin/env python3
"""Automated submitter for ARC-AGI-3 ($850k Track).

Monitors manderson240/cohezion-arc-agi-3-autoharness-solver (v10).
Once KernelWorkerStatus.COMPLETE is reached, automatically submits submission.parquet via Kaggle CLI.
"""

import subprocess
import time


KERNEL = "manderson240/cohezion-arc-agi-3-autoharness-solver"
VERSION = "18"
COMP = "arc-prize-2026-arc-agi-3"
FILE = "submission.parquet"
MSG = "Cohezion v18: Directed Affordance Rarity SearchAgent + BlueQubit QUBO Tie-Breaking + AutoHarness Invariants"

print(f"Monitoring {KERNEL} for completion and submission...")

while True:
    res = subprocess.run(
        ["kaggle", "kernels", "status", KERNEL],
        capture_output=True,
        text=True,
        check=False,
    )
    status_text = res.stdout + res.stderr
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Kernel Status: {status_text.strip()}")

    if "KernelWorkerStatus.COMPLETE" in status_text:
        print("Kernel execution COMPLETE! Submitting to competition...")
        sub_res = subprocess.run(
            [
                "kaggle",
                "competitions",
                "submit",
                "-c",
                COMP,
                "-k",
                KERNEL,
                "-v",
                VERSION,
                "-f",
                FILE,
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
            print("✓ Successfully submitted to ARC-AGI-3!")
            break
        else:
            print(f"Submission returned code {sub_res.returncode}. Quota likely resets at 00:00 UTC (~2.5h). Retrying in 300s...")
            time.sleep(300)
            continue
    elif "KernelWorkerStatus.ERROR" in status_text:
        print("❌ Kernel failed with ERROR.")
        break

    time.sleep(15)
