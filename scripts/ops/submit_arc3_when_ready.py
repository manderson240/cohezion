#!/usr/bin/env python3
"""Automated submitter for ARC-AGI-3 ($850k Track).

Monitors manderson240/cohezion-arc-agi-3-autoharness-solver (v10).
Once KernelWorkerStatus.COMPLETE is reached, automatically submits submission.parquet via Kaggle CLI.
"""

import subprocess
import time


KERNEL = "manderson240/cohezion-arc-agi-3-autoharness-solver"
VERSION = "24"
COMP = "arc-prize-2026-arc-agi-3"
FILE = "submission.parquet"
MSG = "Cohezion v24: Dual-Mode SOTA Engine (Cayley Permutation + Geodesic Nav + 35-step Truncation)"

print(f"Monitoring {KERNEL} for completion and submission...")

while True:
    res = subprocess.run(
        ["kaggle", "kernels", "status", KERNEL],
        capture_output=True,
        text=True,
        check=False,
    )
    status_text = res.stdout + res.stderr
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Kernel Status: {status_text.strip()}", flush=True)

    if "KernelWorkerStatus.COMPLETE" in status_text:
        print("Kernel execution COMPLETE! Submitting to competition...", flush=True)
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
        print("Submission stdout:", sub_res.stdout.strip(), flush=True)
        print("Submission stderr:", sub_res.stderr.strip(), flush=True)
        if sub_res.returncode == 0:
            print("✓ Successfully submitted to ARC-AGI-3!", flush=True)
            break
        else:
            print(f"Submission returned code {sub_res.returncode}. Quota likely resets at 00:00 UTC. Retrying in 300s...", flush=True)
            time.sleep(300)
            continue
    elif "KernelWorkerStatus.ERROR" in status_text:
        print("❌ Kernel failed with ERROR.")
        break

    time.sleep(15)
