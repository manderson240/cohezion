#!/usr/bin/env python3
"""Unified Auto-Submit Watcher for Kaggle Kernels.

Monitors active kernel versions and submits them upon completion:
1. ARC-AGI-2 v11: manderson240/arc-agi-2-fork-lb33-89-20260903 -> arc-prize-2026-arc-agi-2
2. CASMI26 v9: manderson240/casmi26-analog-baseline-fork-cohezion -> enveda-CASMI26-molecule-id-mass-spectra
"""

import subprocess
import sys
import time

KAGGLE_BIN = "/home/mike-anderson/.local/share/uv/tools/kaggle/bin/kaggle"

TARGETS = [
    {
        "kernel": "manderson240/arc-agi-2-fork-lb33-89-20260903",
        "version": 11,
        "comp": "arc-prize-2026-arc-agi-2",
        "file": "submission.json",
        "desc": "Cohezion ARC-AGI-2 SOTA v11: AutoHarness Guard + Dynamic Path Resolution (Topic 704408 Hardening)",
        "done": False,
    },
    {
        "kernel": "manderson240/casmi26-analog-baseline-fork-cohezion",
        "version": 9,
        "comp": "enveda-CASMI26-molecule-id-mass-spectra",
        "file": "submission.csv",
        "desc": "Cohezion CASMI26 SOTA v9: Isomer Fragment Subgraph Reranker on Top 25 (CE lambda_var=0.0)",
        "done": False,
    },
]

print("Starting Unified Auto-Submit Watcher...", flush=True)

for attempt in range(720):  # poll every 20s for up to 4 hours
    all_done = True
    for item in TARGETS:
        if item["done"]:
            continue
        all_done = False
        k = item["kernel"]
        v = item["version"]
        try:
            res = subprocess.run([KAGGLE_BIN, "kernels", "status", k], capture_output=True, text=True)
            status_str = res.stdout.strip()
            if attempt % 6 == 0:
                print(f"[{attempt:3d}] {k} v{v}: {status_str}", flush=True)
            if "COMPLETE" in status_str:
                print(f"✓ {k} v{v} is COMPLETE! Submitting to {item['comp']}...", flush=True)
                cmd = [
                    KAGGLE_BIN, "competitions", "submit",
                    "-c", item["comp"],
                    "-f", item["file"],
                    "-m", item["desc"],
                    "-k", k,
                    "-v", str(v)
                ]
                sub_res = subprocess.run(cmd, capture_output=True, text=True)
                print(f"Submit output for {k}:\n{sub_res.stdout}\n{sub_res.stderr}", flush=True)
                item["done"] = True
            elif "ERROR" in status_str or "CANCELLED" in status_str:
                print(f"✗ {k} v{v} terminated with error: {status_str}", flush=True)
                item["done"] = True
        except Exception as e:
            print(f"Error checking {k}: {e}", flush=True)

    if all_done:
        print("All targets submitted successfully!", flush=True)
        sys.exit(0)

    time.sleep(20)

print("Watcher reached timeout.", flush=True)
