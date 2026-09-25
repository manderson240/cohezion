#!/usr/bin/env python3
"""Monitors manderson240/cohezion-biohub-v6 and submits to Biohub 3D Cell Tracking upon completion."""

import os
import sys
import time
from kaggle.api.kaggle_api_extended import KaggleApi

KERNEL_REF = "manderson240/cohezion-biohub-v6"
COMP_ID = "biohub-cell-tracking-during-development"
SUB_FILE = "submission.csv"
TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 10

api = KaggleApi()
api.authenticate()

print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...")

for attempt in range(720):  # poll every 10s for up to 120 minutes
    status_obj = api.kernels_status(KERNEL_REF)
    status_str = str(getattr(status_obj, "status", status_obj))
    print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✔ Kernel run completed! Automatically submitting v{TARGET_VERSION} to {COMP_ID}...")
        try:
            res = api.competition_submit_code(
                file_name=SUB_FILE,
                message=f"Cohezion Biohub V13 SOTA: Levin Field + Reciprocal Cycle Consistency + Mitotic COM Invariant v{TARGET_VERSION} (LB target 0.972+)",
                competition=COMP_ID,
                kernel=KERNEL_REF,
                kernel_version=TARGET_VERSION,
            )
            print("Submit response:", res)
            sys.exit(0)
        except Exception as e:
            print(f"Submission error: {e}")
            sys.exit(1)
    elif "ERROR" in status_str or "CANCELLED" in status_str:
        print(f"Kernel terminated with status: {status_str}")
        sys.exit(1)

    time.sleep(10)

print("Timed out waiting for kernel completion.")
sys.exit(2)
