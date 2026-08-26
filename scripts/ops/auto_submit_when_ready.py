#!/usr/bin/env python3
"""Auto-Submit Completed Kaggle Kernel Outputs to Competition Leaderboards."""

import subprocess
import time
import os
from pathlib import Path

TARGETS = [
    {
        "comp": "rsna-knee-abnormality-detection",
        "kernel": "manderson240/cohezion-rsna-knee-abnormality-detection-baseline",
        "filename": "submission.csv",
        "message": "Cohezion Multi-View Prior MIL Baseline v4"
    },
    {
        "comp": "biohub-cell-tracking-during-development",
        "kernel": "manderson240/cohezion-biohub-cell-tracking-baseline",
        "filename": "submission.csv",
        "message": "Cohezion Hungarian Bipartite Mitosis Baseline v7"
    }
]

def check_and_submit():
    print("=" * 80)
    print("⏳ MONITORING KERNELS FOR AUTO-SUBMISSION TO LEADERBOARD")
    print("=" * 80)

    for item in TARGETS:
        comp = item["comp"]
        kernel = item["kernel"]
        fname = item["filename"]
        msg = item["message"]

        res = subprocess.run(["kaggle", "kernels", "status", kernel], capture_output=True, text=True)
        status_line = res.stdout.strip()
        print(f"• [{comp}] {kernel} -> {status_line}")

        if "COMPLETE" in status_line:
            out_dir = Path(f"/tmp/kaggle_out/{kernel.split('/')[-1]}")
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Downloading output for {kernel}...")
            subprocess.run(["kaggle", "kernels", "output", kernel, "-p", str(out_dir)], capture_output=True)
            
            sub_file = out_dir / fname
            if sub_file.exists() and sub_file.stat().st_size > 5:
                print(f"  🚀 Submitting {sub_file} to {comp}...")
                sub_res = subprocess.run([
                    "kaggle", "competitions", "submit",
                    "-c", comp,
                    "-f", str(sub_file),
                    "-m", msg
                ], capture_output=True, text=True)
                print(f"  Submission Output: {sub_res.stdout or sub_res.stderr}")
            else:
                print(f"  Notice: {fname} size is {sub_file.stat().st_size if sub_file.exists() else 0} bytes. Standing by.")

if __name__ == "__main__":
    check_and_submit()
