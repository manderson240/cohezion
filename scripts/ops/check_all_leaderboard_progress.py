#!/usr/bin/env python3
"""Check Kaggle Leaderboard Standings, Kernel Statuses, and Submission Scores."""

import subprocess
import json

COMPETITIONS = [
    "arc-prize-2024",
    "rsna-knee-abnormality-detection",
    "biohub-cell-tracking-during-development"
]

KERNELS = [
    "manderson240/cohezion-arc-prize-autoharness-solver",
    "manderson240/cohezion-arc-prize-agi-3-autoharness-solver",
    "manderson240/cohezion-ismcts-cfr-pokemon-tcg",
    "manderson240/cohezion-rsna-knee-abnormality-detection-baseline",
    "manderson240/cohezion-biohub-cell-tracking-baseline"
]

def check_status():
    print("=" * 80)
    print("🏆 CHECKING LIVE KAGGLE LEADERBOARDS & KERNEL STATUS")
    print("=" * 80)

    print("\n--- 1. ACTIVE KERNEL EXECUTION STATUS ---")
    for k in KERNELS:
        res = subprocess.run(["kaggle", "kernels", "status", k], capture_output=True, text=True)
        print(f"• {k} -> {res.stdout.strip()}")

    print("\n--- 2. SUBMISSION HISTORY & LEADERBOARD SCORES ---")
    for c in COMPETITIONS:
        print(f"\n[Competition: {c}]")
        res = subprocess.run(["kaggle", "competitions", "submissions", "-c", c], capture_output=True, text=True)
        lines = res.stdout.strip().split("\n")
        for l in lines[:5]:
            print(f"  {l}")

if __name__ == "__main__":
    check_status()
