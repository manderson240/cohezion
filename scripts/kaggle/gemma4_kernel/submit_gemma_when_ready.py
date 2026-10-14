#!/usr/bin/env python3
"""Monitors gemma-4-developer-agent pending submission and submits submission.zip upon completion.
Synchronized with Recursive Experiential Learning pipeline (Learning 520).
"""

from pathlib import Path
import subprocess
import sys
import time
from kaggle.api.kaggle_api_extended import KaggleApi

COMP_ID = "gemma-4-developer-agent"
ZIP_PATH = "scripts/kaggle/gemma4_kernel/submission.zip"
MSG = "Cohezion Gemma-4 SOTA: 12B Fast-Inference Container + 240s Pytest Timeout + Paced Edit"
CODE_PATH = "scripts/kaggle/gemma4_kernel/package_submission.py"

print(f"Monitoring competition '{COMP_ID}' for pending submissions to clear...", flush=True)

api = KaggleApi()
api.authenticate()

for attempt in range(720):  # poll for up to 12 hours (every 60s)
    try:
        subs = api.competition_submissions(COMP_ID)
        pending = [s for s in subs if "PENDING" in str(s.status).upper()]
        print(f"[{attempt:3d}] Total submissions: {len(subs)}, Pending: {len(pending)}", flush=True)
        if len(pending) == 0:
            print("✓ No pending submissions detected! Dispatching 12B Fast-Inference Agent submission...", flush=True)
            cmd = [
                sys.executable,
                "scripts/kaggle/kaggle_submit.py",
                "file",
                "-c", COMP_ID,
                "-f", ZIP_PATH,
                "-m", MSG,
                "--code-path", CODE_PATH
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            print(res.stdout, res.stderr, flush=True)
            if res.returncode == 0:
                print("✓ Gemma 4 submission succeeded!", flush=True)
                try:
                    sys.path.insert(0, str(WORKSPACE / "scripts" / "kaggle"))
                    from recursive_experiential_learner import audit_and_learn
                    audit_and_learn()
                    print("✓ Triggered recursive experiential learning update.", flush=True)
                except Exception as rel_err:
                    print(f"Note on learner: {rel_err}", flush=True)
                sys.exit(0)
            else:
                print("⚠️ Submission attempt returned non-zero code. Retrying next cycle...", flush=True)
    except Exception as e:
        print(f"⚠️ Error checking submissions: {e}", flush=True)

    time.sleep(60)

print("Timed out waiting for pending submission to clear.", flush=True)
sys.exit(2)
