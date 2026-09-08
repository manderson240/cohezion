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

print(f"Monitoring kernel {KERNEL_REF}...")

for attempt in range(120): # poll for up to 10 minutes
    status_obj = api.kernels_status(KERNEL_REF)
    status_str = str(getattr(status_obj, "status", status_obj))
    print(f"[{attempt:3d}] Status: {status_str}")
    
    if "COMPLETE" in status_str:
        print("✓ Kernel run completed! Submitting to RSNA Knee Abnormality Detection...")
        res = api.competition_submit_code(
            file_name=SUB_FILE,
            message="Cohezion RSNA Knee SOTA Multi-View Ensemble (CoAtNet + Raptor 4-View Rank Average)",
            competition=COMP_ID,
            kernel=KERNEL_REF,
            kernel_version=1
        )
        print("Submit response:", res)
        sys.exit(0)
    elif "ERROR" in status_str or "CANCELLED" in status_str:
        print(f"Kernel terminated with status: {status_str}")
        sys.exit(1)
        
    time.sleep(5)

print("Timed out waiting for kernel completion.")
sys.exit(2)
