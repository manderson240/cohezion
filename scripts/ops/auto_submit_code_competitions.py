#!/usr/bin/env python3
"""Automated Kaggle Code Competition Submitter.

Submits code competition notebook kernels to the live scoring evaluation engine
using the official `-k <kernel>` and `-v <version>` flags.
"""

import subprocess
import time
import sys

SUBMISSIONS = [
    {
        "comp": "arc-prize-2026-arc-agi-2",
        "kernel": "manderson240/cohezion-arc-prize-autoharness-solver",
        "version": "17",
        "file": "submission.json",
        "message": "Cohezion v17: Object Graph DSL + Symmetry + Topological Enclosure"
    },
    {
        "comp": "rsna-knee-abnormality-detection",
        "kernel": "manderson240/cohezion-rsna-knee-abnormality-detection-baseline",
        "version": "4",
        "file": "submission.csv",
        "message": "Cohezion RSNA v4: Multi-View MIL Sequence Prior"
    },
    {
        "comp": "biohub-cell-tracking-during-development",
        "kernel": "manderson240/cohezion-biohub-cell-tracking-baseline",
        "version": "7",
        "file": "submission.csv",
        "message": "Cohezion Biohub v7: Hungarian Bipartite Mitosis Lineage"
    }
]

def submit_all():
    print("=" * 80)
    print("🚀 DISPATCHING OFFICIAL KAGGLE CODE COMPETITION SUBMISSIONS")
    print("=" * 80)
    for sub in SUBMISSIONS:
        cmd = [
            "kaggle", "competitions", "submit",
            "-c", sub["comp"],
            "-k", sub["kernel"],
            "-v", sub["version"],
            "-f", sub["file"],
            "-m", sub["message"]
        ]
        print(f"▶ Submitting {sub['comp']} (Kernel: {sub['kernel']} v{sub['version']})...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(f"  Result: {res.stdout.strip() or res.stderr.strip()}")
        time.sleep(2)
    print("=" * 80)

if __name__ == "__main__":
    submit_all()
