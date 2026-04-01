#!/usr/bin/env python3
"""Continuous submission pipeline for AMD speedrun.

Runs until 7 AM EST, submitting parameter sweep variants with rate limiting.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


END_HOUR = 7  # 7 AM EST
RATE_LIMIT_SECONDS = 610  # 10 min + buffer
STATE_FILE = Path("/home/mike-anderson/dev/cohezion/luma_speedrun/submission_state.json")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def should_continue():
    now = datetime.now()
    return now.hour < END_HOUR


def submit_variant(kernel, variant_file, mode="test"):
    """Submit a variant and return result."""
    cmd = [
        "popcorn-cli",
        "submit",
        str(variant_file),
        "--mode",
        mode,
        "--gpu",
        "MI355X",
        "--leaderboard",
        f"amd-{kernel}",
        "--no-tui",
    ]

    log(f"Submitting {kernel}: {variant_file.name} [{mode}]")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if "error" in result.stderr.lower() or result.returncode != 0:
            log(f"  ERROR: {result.stderr[:200]}")
            return False
        else:
            log(f"  SUCCESS: Submitted")
            return True

    except subprocess.TimeoutExpired:
        log("  TIMEOUT: Submission took too long")
        return False
    except Exception as e:
        log(f"  EXCEPTION: {e}")
        return False


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"tested": [], "leaderboard": [], "last_submit": 0}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main():
    log("=== Continuous Submission Pipeline ===")
    log(f"Running until {END_HOUR}:00 EST")

    # Define variants to test
    variants = {
        "moe": [
            Path(
                "/home/mike-anderson/dev/cohezion/luma_speedrun/variants/moe/submission_block_64.py"
            ),
            Path(
                "/home/mike-anderson/dev/cohezion/luma_speedrun/variants/moe/submission_block_128.py"
            ),
            Path(
                "/home/mike-anderson/dev/cohezion/luma_speedrun/variants/moe/submission_sorting_opus.py"
            ),
        ],
    }

    state = load_state()

    cycle = 0
    while should_continue():
        cycle += 1
        log(f"=== Cycle {cycle} ===")

        # Check rate limit
        time_since_last = time.time() - state["last_submit"]
        if time_since_last < RATE_LIMIT_SECONDS:
            wait_time = RATE_LIMIT_SECONDS - time_since_last
            log(f"Rate limit: waiting {wait_time:.0f}s")
            time.sleep(wait_time)

        # Try each kernel
        for kernel, files in variants.items():
            for variant_file in files:
                if not variant_file.exists():
                    log(f"Skipping missing file: {variant_file}")
                    continue

                variant_id = f"{kernel}:{variant_file.name}"

                # Test mode first
                if variant_id not in state["tested"]:
                    if submit_variant(kernel, variant_file, "test"):
                        state["tested"].append(variant_id)
                        state["last_submit"] = time.time()
                        save_state(state)

                        # Wait before next submission
                        time.sleep(2)

                    if not should_continue():
                        break

                # Leaderboard mode for tested variants
                elif variant_id not in state["leaderboard"]:
                    if submit_variant(kernel, variant_file, "leaderboard"):
                        state["leaderboard"].append(variant_id)
                        state["last_submit"] = time.time()
                        save_state(state)
                        time.sleep(2)

                    if not should_continue():
                        break

        # Small delay between cycles
        if should_continue():
            log("Waiting for next cycle...")
            time.sleep(30)

    log("=== TIME LIMIT REACHED ===")
    log(f"Stopped at {datetime.now().strftime('%H:%M:%S')}")
    log(f"Tested: {len(state['tested'])} variants")
    log(f"Leaderboard: {len(state['leaderboard'])} variants")


if __name__ == "__main__":
    main()
