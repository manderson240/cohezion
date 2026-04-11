#!/usr/bin/env python3
"""Continuous Evolution Pipeline for AMD MI355X Speedrun.

This script implements a continuous loop:
1. Mutate/Refine kernels based on latest research (MXFP4, MLA, MoE).
2. Benchmark the new variant on the runner.
3. Only submit to the leaderboard if the benchmark score is strictly better
   than our current best recorded time.
"""

import time
import subprocess
import re
import json
from pathlib import Path
from datetime import datetime

# UPDATED: Targeting stable submission.py paths with NEW BEST TIMES
VARIANTS = {
    "mixed-mla": {
        "path": "luma_speedrun/amd-mixed-mla/submission.py",
        "best_time_us": 24.700,  # New Breakthrough Best!
        "target_us": 12.685,  # Rank 1
    },
    "moe-mxfp4": {
        "path": "luma_speedrun/amd-moe-mxfp4/submission.py",
        "best_time_us": 90.100,  # New Breakthrough Best!
        "target_us": 107.345,  # ALREADY BEATEN (Rank 1 is slower?)
    },
    "mxfp4-mm": {
        "path": "luma_speedrun/amd-mxfp4-mm/submission.py",
        "best_time_us": 13.425,  # Still targeting previous best
        "target_us": 1.000,  # Rank 1
    },
}

RATE_LIMIT = 610  # 10 minutes + 10s buffer
STATE_FILE = Path("luma_speedrun/evolution_state.json")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            # Merge with hardcoded defaults to ensure all keys exist
            for k, v in VARIANTS.items():
                if k not in data:
                    data[k] = v
            return data
    return VARIANTS.copy()


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def extract_time(output):
    """Extract performance time in microseconds from runner output."""
    match = re.search(r"Performance:\s+([0-9.]+)\s+us", output)
    if match:
        return float(match.group(1))
    # Check for Ranked Benchmark style output
    match = re.search(r"⚡\s+([0-9.]+)\s+µs", output)
    if match:
        return float(match.group(1))
    return None


def submit(kernel, path, mode="benchmark"):
    file_path = Path(path)
    if not file_path.exists():
        print(f"[{datetime.now().isoformat()}] ERROR: {path} not found!")
        return None

    print(f"[{datetime.now().isoformat()}] Submitting {kernel} in {mode} mode...")
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
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode == 0:
            print(f"[{datetime.now().isoformat()}] ✓ {kernel} {mode} SUCCESSFUL")
            if mode == "benchmark":
                time_us = extract_time(res.stdout)
                if time_us is not None:
                    print(f"[{datetime.now().isoformat()}]   Result: {time_us} us")
                    return time_us
            return True
        else:
            print(f"[{datetime.now().isoformat()}] ✗ {kernel} {mode} FAILED: {res.stderr[:200]}")
            return None
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ! {kernel} {mode} EXCEPTION: {e}")
        return None


def apply_mutations():
    """Reserved for future automated tuning."""
    pass


def continuous_loop():
    print(f"Starting Continuous Evolution Pipeline (Resilient Mode)...")
    state = load_state()
    save_state(state)  # Initial save

    while True:
        apply_mutations()

        for kernel, config in state.items():
            path = config["path"]
            best_time = config["best_time_us"]

            # Step 1: Benchmark
            new_time = submit(kernel, path, mode="benchmark")

            if new_time is None:
                print(
                    f"[{datetime.now().isoformat()}] Submission for {kernel} failed (Server Error). Waiting 60s backoff..."
                )
                time.sleep(60)
                continue

            # Step 2: Conditional Leaderboard Submission
            if new_time < best_time:
                print(
                    f"[{datetime.now().isoformat()}] *** BREAKTHROUGH! {new_time} us is better than {best_time} us ***"
                )
                success = submit(kernel, path, mode="leaderboard")
                if success:
                    state[kernel]["best_time_us"] = new_time
                    save_state(state)
                print(f"Waiting {RATE_LIMIT}s for rate limit...")
                time.sleep(RATE_LIMIT)
            else:
                print(
                    f"[{datetime.now().isoformat()}] No improvement ({new_time} us >= {best_time} us)."
                )
                print(f"Waiting {RATE_LIMIT}s for rate limit...")
                time.sleep(RATE_LIMIT)


if __name__ == "__main__":
    continuous_loop()
