#!/usr/bin/env python3
"""Monitors manderson240/cohezion-rsna-knee-sota-multi-view-ensemble and submits to RSNA Knee competition upon completion."""

import time
import sys
import json
from kaggle.api.kaggle_api_extended import KaggleApi

KERNEL_REF = "manderson240/cohezion-rsna-knee-sota-ensemble"
COMP_ID = "rsna-knee-abnormality-detection"
SUB_FILE = "submission.csv"

api = KaggleApi()
api.authenticate()

TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 5
print(f"Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...")

for attempt in range(360):  # poll for up to 60 minutes
    status_obj = api.kernels_status(KERNEL_REF)
    status_str = str(getattr(status_obj, "status", status_obj))
    print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✓ Kernel run completed! Submitting v{TARGET_VERSION} to RSNA Knee Abnormality Detection...")
        res = api.competition_submit_code(
            file_name=SUB_FILE,
            message=f"Cohezion RSNA Knee SOTA Multi-View Logit-Calibrated Ensemble v{TARGET_VERSION} (CoAtNet + Raptor + DINOv2 on NvidiaTeslaT4)",
            competition=COMP_ID,
            kernel=KERNEL_REF,
            kernel_version=TARGET_VERSION,
        )
        print("Submit response:", res)
        sys.exit(0)
    elif "ERROR" in status_str or "CANCELLED" in status_str:
        print(f"Kernel terminated with status: {status_str}")
        sys.exit(1)

    time.sleep(10)

print("Timed out waiting for kernel completion.")
sys.exit(2)
