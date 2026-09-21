#!/usr/bin/env python3
"""Auto-submit ARC-AGI-2 kernel via Kaggle API client."""

import sys
from kaggle.api.kaggle_api_extended import KaggleApi

COMP_ID = "arc-prize-2026-arc-agi-2"
KERNEL_REF = "manderson240/arc-agi-2-fork-lb33-89-20260903"
VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 4
FILE_NAME = "submission.json"

api = KaggleApi()
api.authenticate()

print(f"Submitting {KERNEL_REF} v{VERSION} to {COMP_ID}...")
try:
    res = api.competition_submit_code(
        file_name=FILE_NAME,
        message=f"Cohezion AutoHarness Invariants + Qwen3-4B LoRA L4 v{VERSION}",
        competition=COMP_ID,
        kernel=KERNEL_REF,
        kernel_version=VERSION,
    )
    print("✅ Submission successful:", res)
except Exception as e:
    print("❌ Submission failed:", e)
    sys.exit(1)
