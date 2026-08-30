#!/usr/bin/env python3
"""Audits Kaggle Daily Submission Limits & Recent Statuses Across All Active Competitions."""

import subprocess
import json

COMPETITIONS = [
    "arc-prize-2026-arc-agi-2",
    "arc-prize-2026-arc-agi-3",
    "kaggriculture",
    "rsna-knee-abnormality-detection",
    "biohub-cell-tracking-during-development",
    "pokemon-tcg-ai",
    "measuring-progress-toward-agi",
    "neurogolf-2026",
    "birdclef-2026",
    "aimo-progress-prize-3"
]

def check_competition_submissions():
    print("\n" + "=" * 115)
    print("📊 COMPREHENSIVE KAGGLE SUBMISSION QUOTA & STATUS AUDIT")
    print("=" * 115)

    for comp in COMPETITIONS:
        try:
            res = subprocess.run(
                ["kaggle", "competitions", "submissions", comp],
                capture_output=True,
                text=True,
                timeout=15
            )
            out_lines = [line for line in res.stdout.splitlines() if line.strip()]
            print(f"\n🏆 Competition: `{comp}`")
            if res.returncode == 0 and len(out_lines) > 0:
                for l in out_lines[:4]:  # Show top lines / headers + last 3 submissions
                    print(f"   {l}")
            else:
                print(f"   Notice / Stderr: {res.stderr.strip()[:100] if res.stderr else 'No prior submissions'}")
        except Exception as e:
            print(f"   Error checking `{comp}`: {e}")

    print("\n" + "=" * 115 + "\n")

if __name__ == "__main__":
    check_competition_submissions()
