#!/usr/bin/env python3
"""Fetch enrolled competitions, submission scores, and leaderboard standings via Kaggle API."""

import subprocess
import json

COMPETITIONS = [
    "arc-prize-2024",
    "rsna-knee-abnormality-detection",
    "biohub-cell-tracking-during-development",
    "measuring-progress-toward-agi",
    "birdclef-2026",
    "aimo-progress-prize"
]

def fetch_details():
    print("=" * 90)
    print("🏆 KAGGLE ENROLLED COMPETITIONS, SUBMISSIONS & LEADERBOARD STANDINGS")
    print("=" * 90)

    # 1. List user's active competitions
    print("\n--- 1. ACTIVE / ENROLLED COMPETITIONS ---")
    res_list = subprocess.run(["kaggle", "competitions", "list", "--user"], capture_output=True, text=True)
    if res_list.stdout.strip():
        print(res_list.stdout.strip())
    else:
        print("Standard active list:")
        res_all = subprocess.run(["kaggle", "competitions", "list", "-s", "2026"], capture_output=True, text=True)
        print(res_all.stdout.strip()[:1000])

    # 2. Submissions & Leaderboard ranks for known target tracks
    print("\n--- 2. DETAILED TRACK STATUS & SUBMISSION SCORES ---")
    for comp in COMPETITIONS:
        print(f"\n📁 [Competition: {comp}]")
        sub_res = subprocess.run(["kaggle", "competitions", "submissions", "-c", comp], capture_output=True, text=True)
        if sub_res.stdout.strip():
            print("  Submissions:")
            for line in sub_res.stdout.strip().split("\n")[:6]:
                print(f"    {line}")
        else:
            print("  Submissions: (No active submission records or restricted API view)")

        lb_res = subprocess.run(["kaggle", "competitions", "leaderboard", "-c", comp, "--show"], capture_output=True, text=True)
        if lb_res.stdout.strip():
            print("  Top Leaderboard Benchmark:")
            for line in lb_res.stdout.strip().split("\n")[:5]:
                print(f"    {line}")
        else:
            print("  Leaderboard: (Private / in evaluation / API restricted)")

if __name__ == "__main__":
    fetch_details()
