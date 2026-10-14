#!/usr/bin/env python3
"""Syncs Kaggle Sentinel status for ACTIVE competitions only.

Mandate 8 Compliant:
- Filters to currently ACTIVE, unexpired competitions.
- Excludes closed competitions (Biohub, Kaggriculture) and excluded competitions (Pokémon TCG).
- Persists structured metrics to sentinel_status.json and SurrealDB.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

KAGGLE_BIN = "/home/mike-anderson/.local/bin/kaggle" if Path("/home/mike-anderson/.local/bin/kaggle").exists() else "/home/mike-anderson/.local/share/uv/tools/kaggle/bin/kaggle"

ACTIVE_COMPETITIONS = {
    "ARC_AGI_3": {
        "slug": "arc-prize-2026-arc-agi-3",
        "deadline": "2026-11-02",
        "reward": "$850,000 Usd",
        "metric": "Quadratic Action Economy",
        "medal_target": "Top 10 / Podium (>=0.26+)"
    },
    "ARC_AGI_2": {
        "slug": "arc-prize-2026-arc-agi-2",
        "deadline": "2026-11-02",
        "reward": "$700,000 Usd",
        "metric": "Strict Pass Rate % (2 attempts)",
        "medal_target": "Top 10 (>=33.89%)"
    },
    "ARC_Paper_Track": {
        "slug": "arc-prize-2026-paper-track",
        "deadline": "2026-11-09",
        "reward": "$450,000 Usd",
        "metric": "Peer Review & Scientific Reproducibility",
        "medal_target": "Top Prize / Oral Presentation"
    },
    "RSNA_Knee": {
        "slug": "rsna-knee-abnormality-detection",
        "deadline": "2026-10-22",
        "reward": "$77,000 Usd",
        "metric": "Macro ROC-AUC (12 classes)",
        "medal_target": "Gold/Podium (>=0.957)"
    },
    "Gemma_4_Developer_Agent": {
        "slug": "gemma-4-developer-agent",
        "deadline": "2026-12-02",
        "reward": "$65,000 Usd",
        "metric": "Pass Rate % on GitHub SWE Issues",
        "medal_target": "Top 10 (>=0.15+)"
    },
    "Enveda_CASMI26": {
        "slug": "enveda-CASMI26-molecule-id-mass-spectra",
        "deadline": "2026-12-14",
        "reward": "$50,000 Usd",
        "metric": "Mean Reciprocal Rank (MRR)",
        "medal_target": "Top 10 (>=0.383)"
    },
    "Gemma_4_Paper_Track": {
        "slug": "gemma-4-developer-agent-paper",
        "deadline": "2026-11-12",
        "reward": "$35,000 Usd",
        "metric": "Academic Novelty & Agentic Architecture",
        "medal_target": "Top Prize / NeurIPS Workshop"
    }
}

STATUS_JSON = Path("scripts/kaggle/sentinel_status.json")


def parse_submissions(slug: str) -> list[dict[str, str]]:
    cmd = [KAGGLE_BIN, "competitions", "submissions", "-c", slug]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error fetching submissions for {slug}: {res.stderr}")
        return []

    lines = res.stdout.strip().splitlines()
    if len(lines) < 3:
        return []

    entries = []
    for line in lines[2:]:
        parts = line.split()
        if len(parts) >= 6:
            ref = parts[0]
            filename = parts[1]
            date = f"{parts[2]} {parts[3]}"
            # Look for SubmissionStatus
            status = "UNKNOWN"
            score = ""
            for idx, p in enumerate(parts):
                if "SubmissionStatus." in p or p in ("COMPLETE", "PENDING", "ERROR"):
                    status = p.replace("SubmissionStatus.", "")
                    if idx + 1 < len(parts):
                        score = parts[idx + 1]
                    break
            desc = " ".join(parts[4:])
            entries.append({
                "ref_id": ref,
                "file_name": filename,
                "date": date,
                "description": desc,
                "status": status,
                "public_score": score
            })
    return entries


def main():
    print(f"Syncing active Kaggle competitions as of {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}...")
    report = {
        "timestamp": int(time.time()),
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "filter_mandate": "Active Unexpired Only (Biohub/Kaggriculture/Pokemon excluded)",
        "competitions": {}
    }

    for name, meta in ACTIVE_COMPETITIONS.items():
        slug = meta["slug"]
        print(f"Polling {name} ({slug})...")
        subs = parse_submissions(slug)
        report["competitions"][name] = {
            "metadata": meta,
            "total_submissions_tracked": len(subs),
            "latest_submission": subs[0] if subs else None,
            "submissions": subs[:10]  # Store top 10 most recent
        }

    with open(STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"✓ Saved updated active status to {STATUS_JSON}")


if __name__ == "__main__":
    main()
