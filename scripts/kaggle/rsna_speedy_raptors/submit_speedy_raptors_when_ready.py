#!/usr/bin/env python3
"""Monitors manderson240/cohezion-rsna-speedy-raptors-fork-0922 and automatically dispatches submission upon completion.
====================================================================================================================
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

KERNEL_REF = "manderson240/cohezion-rsna-speedy-raptors-fork-0922"
COMP_ID = "rsna-knee-abnormality-detection"
SUB_FILE = "submission.csv"

PYTHON_BIN = sys.executable
KAGGLE_BIN = ".venv/bin/kaggle"
TARGET_VERSION = int(sys.argv[1]) if len(sys.argv) > 1 else 4
CODE_PATH = "scripts/kaggle/rsna_speedy_raptors/cohezion-rsna-speedy-raptors-fork-0922.ipynb"

print(f"Monitoring kernel {KERNEL_REF} for version {TARGET_VERSION}...", flush=True)

for attempt in range(1080):  # poll for up to 180 minutes (every 10s)
    res = subprocess.run([KAGGLE_BIN, "kernels", "status", KERNEL_REF], capture_output=True, text=True)
    status_str = res.stdout.strip()
    if attempt % 6 == 0 or "COMPLETE" in status_str:
        print(f"[{attempt:3d}] Status: {status_str}", flush=True)

    if "COMPLETE" in status_str:
        print(f"✓ Kernel run completed! Submitting v{TARGET_VERSION} to RSNA Knee Abnormality Detection...", flush=True)
        sub_msg = (
            f"Cohezion RSNA Knee SOTA v29: Speedy Raptors + NvidiaL4 + "
            f"12x12 Clinical Prior Copula Coupling + Guardrails (Daily Harvest)"
        )
        submit_cmd = [
            PYTHON_BIN,
            "scripts/kaggle/kaggle_submit.py",
            "notebook",
            "-c", COMP_ID,
            "-k", KERNEL_REF,
            "-v", str(TARGET_VERSION),
            "-f", SUB_FILE,
            "-m", sub_msg,
            "--creator-id", "rsna-speedy-raptors-creator",
            "--verifier-id", "independent-rsna-auditor",
            "--code-path", CODE_PATH,
            "-w",
        ]
        sub_res = subprocess.run(submit_cmd, capture_output=True, text=True)
        print(sub_res.stdout, sub_res.stderr, flush=True)
        sys.exit(sub_res.returncode)
    elif "ERROR" in status_str or "CANCELLED" in status_str:
        print(f"Kernel terminated with status: {status_str}", flush=True)
        sys.exit(1)

    time.sleep(10)

print("Timed out waiting for kernel completion.", flush=True)
sys.exit(2)
