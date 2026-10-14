"""Comprehensive Kaggle Competition Metadata & Rules Harvester (SDK Compliant)."""

import json
import subprocess
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

COMPETITIONS = [
    "arc-prize-2026-arc-agi-2",
    "arc-prize-2026-arc-agi-3",
    "enveda-CASMI26-molecule-id-mass-spectra",
    "rsna-knee-abnormality-detection",
    "gemma-4-developer-agent",
    "nfl-big-data-bowl-2027",
]

api = KaggleApi()
api.authenticate()

all_intel = {}

for comp in COMPETITIONS:
    print(f"=== Harvesting {comp} ===")
    intel = {"id": comp}
    
    # 1. File List & Sizes via files_list or CLI
    try:
        res = subprocess.run(["kaggle", "competitions", "files", "-c", comp], capture_output=True, text=True, timeout=15)
        intel["files_raw"] = res.stdout.strip()
    except Exception as e:
        intel["files_error"] = str(e)

    # 2. Leaderboard limits & submission constraints via CLI
    try:
        res = subprocess.run(["kaggle", "competitions", "submission-limits", comp], capture_output=True, text=True, timeout=15)
        intel["submission_limits"] = res.stdout.strip()
    except Exception as e:
        intel["submission_limits_error"] = str(e)

    # 3. Competition search / listing details
    try:
        res = subprocess.run(["kaggle", "competitions", "list", "--search", comp], capture_output=True, text=True, timeout=15)
        intel["listing_info"] = res.stdout.strip()
    except Exception as e:
        intel["listing_error"] = str(e)

    # 4. Top forum discussions for secret sauce / pitfalls
    try:
        res = subprocess.run(["kaggle", "competitions", "topics", "-c", comp, "--sort-by", "votes", "--page-size", "5"], capture_output=True, text=True, timeout=15)
        intel["top_discussions"] = res.stdout.strip()
    except Exception as e:
        intel["discussions_error"] = str(e)

    all_intel[comp] = intel

out_path = Path("docs/research/kaggle_official_competition_intelligence.json")
out_path.write_text(json.dumps(all_intel, indent=2), encoding="utf-8")
print(f"✓ Successfully harvested all competition metadata into {out_path}")
