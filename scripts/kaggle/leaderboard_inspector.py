#!/usr/bin/env python3
"""Kaggle Leaderboard Inspector & Ascent Tracker
=============================================
Automates full leaderboard extraction via Kaggle CLI, parses exact team ranks,
computes score gaps to Rank 1, 3, and 10, calculates actually winnable payouts,
and synchronizes findings with SurrealDB.

Usage:
    uv run python scripts/kaggle/leaderboard_inspector.py [--sync-surreal]
"""

from __future__ import annotations

import argparse
import base64
import csv
import glob
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ACTIVE_COMPETITIONS = [
    {
        "id": "biohub-cell-tracking-during-development",
        "name": "Biohub 3D Cell Tracking",
        "deadline": "2026-09-29",
        "winnable": "$8,000 - $18,000",
        "target": "Top 3 Podium (1st Target)",
        "twin": "Dr. Barbara McClintock & Dr. Ilya Prigogine",
        "direction": "higher",
    },
    {
        "id": "kaggriculture",
        "name": "Kaggriculture Simulation",
        "deadline": "2026-09-30",
        "winnable": "$5,000 (Flat)",
        "target": "Top 10 Finisher",
        "twin": "Dr. John von Neumann & Dr. Claude Shannon",
        "direction": "higher",
    },
    {
        "id": "rsna-knee-abnormality-detection",
        "name": "RSNA Knee Abnormality",
        "deadline": "2026-10-22",
        "winnable": "$6,500 - $17,000",
        "target": "Top 5 (1st Target)",
        "twin": "Dr. Richard Feynman & Dr. Barbara McClintock",
        "direction": "higher",  # Kaggle score is reported as AUC / 1-logloss
    },
    {
        "id": "arc-prize-2026-arc-agi-3",
        "name": "ARC Prize 2026: ARC-AGI-3",
        "deadline": "2026-11-02",
        "winnable": "$20,000 - $75,000",
        "target": "Top 3 Podium",
        "twin": "Dr. John von Neumann & Dr. Richard Feynman",
        "direction": "higher",
    },
    {
        "id": "arc-prize-2026-arc-agi-2",
        "name": "ARC Prize 2026: ARC-AGI-2",
        "deadline": "2026-11-02",
        "winnable": "$25,000 - $100,000",
        "target": "Top 3 Podium",
        "twin": "Dr. John von Neumann & Dr. Claude Shannon",
        "direction": "higher",
    },
    {
        "id": "gemma-4-developer-agent",
        "name": "Google Gemma 4 Developer Agent",
        "deadline": "2026-12-02",
        "winnable": "$7,000 - $25,000",
        "target": "Top 5 (1st Target)",
        "twin": "Dr. Leslie Lamport & Dr. John von Neumann",
        "direction": "higher",
    },
    {
        "id": "enveda-CASMI26-molecule-id-mass-spectra",
        "name": "Enveda CASMI26 Molecule ID",
        "deadline": "2026-12-14",
        "winnable": "$9,000 - $16,000",
        "target": "Top 3 Podium",
        "twin": "Dr. Ilya Prigogine & Dr. Claude Shannon",
        "direction": "higher",
    },
]

KAGGLE_USER = "manderson240"
CACHE_DIR = Path("/tmp/lb_all")


def download_and_extract_leaderboard(comp_id: str) -> Path | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = CACHE_DIR / f"{comp_id}.zip"
    
    # Download leaderboard zip
    subprocess.run(
        ["kaggle", "competitions", "leaderboard", comp_id, "-d", "-p", str(CACHE_DIR), "-q"],
        capture_output=True,
        text=True,
    )
    
    if zip_path.exists():
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(CACHE_DIR)
        zip_path.unlink()
        
    matched = list(CACHE_DIR.glob(f"{comp_id}-publicleaderboard*.csv"))
    if matched:
        return sorted(matched, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return None


def inspect_leaderboard(comp_meta: dict[str, str]) -> dict[str, Any]:
    comp_id = comp_meta["id"]
    csv_file = download_and_extract_leaderboard(comp_id)
    
    if not csv_file or not csv_file.exists():
        return {
            "comp": comp_meta,
            "error": "Failed to download leaderboard CSV",
        }
        
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        
    total_teams = len(reader)
    our_row = None
    for row in reader:
        members = row.get("TeamMemberUserNames", "")
        tname = row.get("TeamName", "")
        if KAGGLE_USER in members or KAGGLE_USER in tname:
            our_row = row
            break
            
    rank_str = our_row.get("Rank", our_row.get("\ufeffRank", "N/A")) if our_row else "N/A"
    score_str = our_row.get("Score", "N/A") if our_row else "N/A"
    
    r1_score = reader[0].get("Score", "N/A") if total_teams >= 1 else "N/A"
    r3_score = reader[2].get("Score", "N/A") if total_teams >= 3 else "N/A"
    r10_score = reader[9].get("Score", "N/A") if total_teams >= 10 else "N/A"
    
    gap_r3 = "N/A"
    try:
        if r3_score != "N/A" and score_str != "N/A":
            diff = float(r3_score) - float(score_str)
            gap_r3 = f"{diff:+.4f}" if comp_meta["direction"] == "higher" else f"{-diff:+.4f}"
    except ValueError:
        pass
        
    percentile = "N/A"
    if rank_str.isdigit() and total_teams > 0:
        percentile = f"Top {(int(rank_str) / total_teams * 100):.1f}%"
        
    # Compute days left
    try:
        deadline_dt = datetime.strptime(comp_meta["deadline"], "%Y-%m-%d").date()
        today_dt = datetime.now().date()
        days_left = (deadline_dt - today_dt).days
    except Exception:
        days_left = -1

    return {
        "comp": comp_meta,
        "rank": rank_str,
        "score": score_str,
        "total_teams": total_teams,
        "percentile": percentile,
        "r1_score": r1_score,
        "r3_score": r3_score,
        "r10_score": r10_score,
        "gap_r3": gap_r3,
        "days_left": days_left,
    }


def sync_to_surrealdb(reports: list[dict[str, Any]]) -> None:
    statements = ["USE NS cohezion DB main;"]
    for r in reports:
        if "error" in r:
            continue
        c = r["comp"]
        table_id = c["id"].replace("-", "_")
        sql = f"""
UPSERT competition:{table_id} CONTENT {{
    name: '{c["name"]}',
    deadline: '{c["deadline"]}T23:59:59Z',
    days_remaining: {r["days_left"]},
    current_rank: {r["rank"] if r["rank"].isdigit() else 'null'},
    total_teams: {r["total_teams"]},
    percentile: '{r["percentile"]}',
    current_score: {r["score"] if r["score"] != 'N/A' else 'null'},
    rank_1_score: {r["r1_score"] if r["r1_score"] != 'N/A' else 'null'},
    rank_3_score: {r["r3_score"] if r["r3_score"] != 'N/A' else 'null'},
    gap_to_podium: '{r["gap_r3"]}',
    winnable_payout: '{c["winnable"]}',
    target_position: '{c["target"]}',
    scientist_twin: '{c["twin"]}',
    last_audited: time::now()
}};
"""
        statements.append(sql.strip())
        
    full_sql = "\n".join(statements)
    req = urllib.request.Request(
        "http://localhost:8001/sql",
        data=full_sql.encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    auth = base64.b64encode(b"root:root").decode("ascii")
    req.add_header("Authorization", f"Basic {auth}")
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[SurrealDB] Successfully synchronized {len(reports)} competition records.")
    except Exception as e:
        print(f"[SurrealDB Error] Failed to sync: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaggle Leaderboard Inspector")
    parser.add_argument("--sync-surreal", action="store_true", default=True, help="Sync to SurrealDB")
    args = parser.parse_args()

    print("=" * 115)
    print("COHEZION KAGGLE LEADERBOARD ASSET & PODIUM GAP AUDITOR")
    print(f"Timestamp: {datetime.now(UTC).isoformat()} | User: {KAGGLE_USER}")
    print("=" * 115)
    
    reports = []
    for c in ACTIVE_COMPETITIONS:
        report = inspect_leaderboard(c)
        reports.append(report)

    # Sort reports by days left
    reports.sort(key=lambda r: r.get("days_left", 999))

    headers = [
        "Priority",
        "Competition",
        "Days Left",
        "Our Rank / Total",
        "Percentile",
        "Our Score",
        "Rank 1",
        "Rank 3",
        "Gap to R3",
        "Winnable Payout",
        "Lead Scientist",
    ]
    
    print(f"{headers[0]:<8} | {headers[1]:<30} | {headers[2]:<9} | {headers[3]:<16} | {headers[4]:<11} | {headers[5]:<9} | {headers[6]:<8} | {headers[7]:<8} | {headers[8]:<9} | {headers[9]:<18} | {headers[10]}")
    print("-" * 155)

    for i, r in enumerate(reports, start=1):
        if "error" in r:
            print(f"{i:<8} | {r['comp']['name']:<30} | ERROR: {r['error']}")
            continue
        c = r["comp"]
        rank_total = f"{r['rank']} / {r['total_teams']}"
        days_str = f"{r['days_left']}d"
        print(
            f"{i:<8} | {c['name']:<30} | {days_str:<9} | {rank_total:<16} | {r['percentile']:<11} | {r['score']:<9} | {r['r1_score']:<8} | {r['r3_score']:<8} | {r['gap_r3']:<9} | {c['winnable']:<18} | {c['twin']}"
        )

    print("=" * 155)
    
    if args.sync_surreal:
        sync_to_surrealdb(reports)


if __name__ == "__main__":
    main()
