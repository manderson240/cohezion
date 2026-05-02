#!/usr/bin/env python3
"""Deploy Deep Breakthrough variants for AMD MI355X Speedrun.

This script submits the stream-aware custom HIP breakthroughs for MLA, MoE, and GEMM.
"""

import subprocess
import time
from pathlib import Path


# Breakthrough variants
BREAKTHROUGHS = [
    ("mixed-mla", "luma_speedrun/amd-mixed-mla/submission_breakthrough_mla.py"),
    ("moe-mxfp4", "luma_speedrun/amd-moe-mxfp4/submission_breakthrough_moe.py"),
    ("mxfp4-mm", "luma_speedrun/amd-mxfp4-mm/submission_breakthrough_gemm.py"),
]

RATE_LIMIT = 610  # 10 minutes + 10s buffer


def submit(kernel, path, mode="benchmark"):
    file_path = Path(path)
    if not file_path.exists():
        print(f"ERROR: {path} not found!")
        return False

    print(f"Submitting breakthrough for {kernel} in {mode} mode...")

    cmd = [
        "popcorn-cli",
        "submit",
        str(file_path),
        "--mode",
        mode,
        "--gpu",
        "MI355X",
        "--leaderboard",
        f"amd-{kernel}",
        "--no-tui",
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode == 0:
            print(f"✓ {kernel} {mode} SUCCESSFUL")
            # Parse output for timing if possible
            if "Performance:" in res.stdout:
                print(f"  Result: {res.stdout.split('Performance:')[1].split('\n')[0].strip()}")
            return True
        else:
            print(f"✗ {kernel} {mode} FAILED: {res.stderr[:200]}")
            return False
    except Exception as e:
        print(f"! {kernel} {mode} EXCEPTION: {e}")
        return False


def deploy():
    print("Starting Deep Breakthrough Deployment & Testing...")

    # Phase 1: Benchmark all to verify performance and correctness
    print("\n--- PHASE 1: BENCHMARKING ---")
    results = {}
    for kernel, path in BREAKTHROUGHS:
        results[kernel] = submit(kernel, path, mode="benchmark")
        print(f"Waiting {RATE_LIMIT}s for rate limit...")
        time.sleep(RATE_LIMIT)

    # Phase 2: Official Leaderboard Submission for successful ones
    print("\n--- PHASE 2: LEADERBOARD SUBMISSION ---")
    for kernel, path in BREAKTHROUGHS:
        if results.get(kernel):
            submit(kernel, path, mode="leaderboard")
            print(f"Waiting {RATE_LIMIT}s for rate limit...")
            time.sleep(RATE_LIMIT)
        else:
            print(f"Skipping {kernel} due to benchmark failure.")


if __name__ == "__main__":
    deploy()
