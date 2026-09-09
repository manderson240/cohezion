#!/usr/bin/env python3
"""Generates and uploads an authentic ARC-AGI submission to Kaggle."""

import json
import os
import subprocess
import time
import numpy as np

TEST_CHALLENGES = "data/arc_prize/arc-agi_test_challenges.json"
SUBMISSION_FILE = "data/arc_prize/submission.json"

def generate_submission():
    print("\n" + "=" * 115)
    print("🚀 GENERATING AUTHENTIC ARC PRIZE 2026 SUBMISSION KERNEL")
    print("=" * 115)

    with open(TEST_CHALLENGES, "r") as f:
        test_tasks = json.load(f)

    submission_dict = {}
    for task_id, task in test_tasks.items():
        submission_dict[task_id] = []
        for test_case in task["test"]:
            inp = test_case["input"]
            # ARC submission format: 2 candidate predictions per test pair
            attempt_1 = inp # Baseline 1: Identity mapping
            attempt_2 = np.rot90(np.array(inp), 2).tolist() # Baseline 2: 180-deg rotation
            submission_dict[task_id].append({
                "attempt_1": attempt_1,
                "attempt_2": attempt_2
            })

    with open(SUBMISSION_FILE, "w") as f:
        json.dump(submission_dict, f)

    print(f"  ✓ Generated submission for {len(submission_dict)} test tasks ({SUBMISSION_FILE})")

    # Upload to Kaggle via CLI
    cmd = [
        "kaggle", "competitions", "submit",
        "-c", "arc-prize-2026-arc-agi-2",
        "-f", SUBMISSION_FILE,
        "-m", f"Cohezion Sovereign Swarm Baseline {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
    ]
    print(f"\n▶ Uploading to Kaggle Leaderboard: `{' '.join(cmd)}`...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("  Output:", res.stdout)
    if res.stderr:
        print("  Error:", res.stderr)

    print("=" * 115 + "\n")

if __name__ == "__main__":
    generate_submission()
