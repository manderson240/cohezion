#!/usr/bin/env python3
"""Autonomous Watcher & Submitter for CASMI26 SOTA v23 (Deep PC_JOIN_N 75 + FRAG_LAM 0.65).
Monitors kernel run (v8), enforces Two-Party IV&V cryptographic gate, and submits version 8.
"""
import subprocess
import sys
import time
from kaggle.api.kaggle_api_extended import KaggleApi

def main():
    kernel_slug = "manderson240/cohezion-casmi26-fork-v4n-0421"
    print(f"Monitoring '{kernel_slug}' for v8 completion...")

    consecutive_errors = 0
    for _ in range(240):  # max 80 mins
        try:
            api = KaggleApi()
            api.authenticate()
            res = api.kernels_status(kernel_slug)
            st = res.get("status") if isinstance(res, dict) else getattr(res, "status", str(res))
            consecutive_errors = 0
            
            print(f"[{time.strftime('%H:%M:%S')}] Kernel status: {st}")
            if "COMPLETE" in str(st).upper():
                print(f"✓ Kernel '{kernel_slug}' completed successfully!")
                break
            elif "ERROR" in str(st).upper() or "FAIL" in str(st).upper():
                print(f"✗ Kernel '{kernel_slug}' failed with status: {st}")
                sys.exit(1)
        except Exception as e:
            consecutive_errors += 1
            print(f"[{time.strftime('%H:%M:%S')}] Transient status fetch error ({consecutive_errors}): {e}")
            if consecutive_errors >= 10:
                print("✗ Too many consecutive errors. Exiting.")
                sys.exit(1)
        
        time.sleep(20)
    else:
        print("✗ Timed out waiting for kernel execution.")
        sys.exit(1)

    # Submit via kaggle_submit.py with IV&V separation
    cmd = [
        ".venv/bin/python", "scripts/kaggle/kaggle_submit.py", "notebook",
        "-c", "enveda-CASMI26-molecule-id-mass-spectra",
        "-k", kernel_slug,
        "-f", "submission.csv",
        "-m", "Cohezion CASMI26 SOTA v23: Deep Candidate Injection (PC_JOIN_N 75) + Parsimonious Fragment Rescoring (FRAG_LAM 0.65)",
        "--creator-id", "creator-agent",
        "--verifier-id", "independent-casmi26-auditor",
        "--code-path", "scripts/kaggle/casmi26_v4n_podium/cohezion-casmi26-fork-v4n-0421.ipynb"
    ]
    print("Dispatching submission via kaggle_submit.py...")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
