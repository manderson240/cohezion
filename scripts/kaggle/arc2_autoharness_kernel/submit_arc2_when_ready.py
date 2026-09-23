#!/usr/bin/env python3
"""Automated submission script for ARC-AGI-2 when daily allowance unlocks."""

import os
import sys
import time
from kaggle.api.kaggle_api_extended import KaggleApi

KERNEL_REF = "manderson240/cohezion-arc-agi-2-autoharness-solver"
COMP_ID = "arc-prize-2026-arc-agi-2"
SUB_FILE = "submission.json"
TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 10

api = KaggleApi()
api.authenticate()

print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...")

# 1. Wait for kernel run to complete
for attempt in range(720):  # poll every 10s for up to 120 minutes
    status_obj = api.kernels_status(KERNEL_REF)
    status_str = str(getattr(status_obj, "status", status_obj))
    print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✔ Kernel run completed! Attempting submission of v{TARGET_VERSION} to {COMP_ID}...")
        break
    elif "ERROR" in status_str or "CANCELLED" in status_str:
        print(f"✘ Kernel terminated with error: {status_str}")
        sys.exit(1)
    time.sleep(10)

# 2. Submit with allowance retry loop
while True:
    try:
        res = api.competition_submit_code(
            file_name=SUB_FILE,
            message=f"Cohezion ARC-AGI-2 v{TARGET_VERSION}: Dynamic Path Walking + Poincare Geodesic Beam + AutoHarness Verifier",
            competition=COMP_ID,
            kernel=KERNEL_REF,
            kernel_version=TARGET_VERSION,
        )
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully submitted! Response:", res)
        sys.exit(0)
    except Exception as e:
        err_text = ""
        if hasattr(e, "response") and hasattr(e.response, "text"):
            err_text = e.response.text
        else:
            err_text = str(e)
            
        if "daily Submission allowance" in err_text:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Daily allowance not yet available (resets daily UTC). Waiting 30 minutes...", flush=True)
            time.sleep(1800)
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Submission response: {err_text}")
            if "already submitted" in err_text.lower() or "success" in err_text.lower():
                sys.exit(0)
            time.sleep(60)
