#!/usr/bin/env python3
"""Filter and display only ACTIVE (unexpired) Kaggle competitions for 2026."""

from datetime import datetime, timezone
import json

COMPETITIONS = [
    {
        "name": "ARC Prize 2026 (ARC-AGI-3)",
        "slug": "arc-prize-2026-arc-agi-3",
        "reward": "$850,000",
        "deadline": "2026-11-02 23:59:00",
        "teamCount": 2558,
        "category": "Featured",
        "status": "Active / Deployed Kernel v11 (2D NCA + Dual GPU Swarm)"
    },
    {
        "name": "ARC Prize 2026 (ARC-AGI-2)",
        "slug": "arc-prize-2026-arc-agi-2",
        "reward": "$700,000",
        "deadline": "2026-11-02 23:59:00",
        "teamCount": 1647,
        "category": "Featured",
        "status": "Active / Deployed Kernel v10 (Rank #1638 / Climbing)"
    },
    {
        "name": "ARC Prize 2026 (Paper Track)",
        "slug": "arc-prize-2026-paper-track",
        "reward": "$450,000",
        "deadline": "2026-11-09 23:59:00",
        "teamCount": 155,
        "category": "Featured",
        "status": "Active / FLUME Latent Manifold Paper Ready"
    },
    {
        "name": "Pokémon TCG AI Battle Challenge",
        "slug": "pokemon-tcg-ai-battle-challenge-strategy",
        "reward": "$240,000",
        "deadline": "2026-09-13 23:59:00",
        "teamCount": 515,
        "category": "Featured",
        "status": "Active / Deployed Kernel v7 (Legality Masking + PBS)"
    }
]

now_utc = datetime(2026, 8, 26, 20, 46, 0)

print("=" * 85)
print("🎯 ACTIVE (UNEXPIRED) ENROLLED KAGGLE COMPETITIONS")
print(f"Current Date: {now_utc.strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 85)

active_list = []
for c in COMPETITIONS:
    dl = datetime.strptime(c["deadline"], "%Y-%m-%d %H:%M:%S")
    if dl > now_utc:
        days_left = (dl - now_utc).days
        active_list.append((c, days_left))

for c, days in active_list:
    print(f"\n🏆 {c['name']}")
    print(f"   • Prize Pool: {c['reward']} | Category: {c['category']}")
    print(f"   • Deadline: {c['deadline']} ({days} days remaining)")
    print(f"   • Competitors: {c['teamCount']} teams")
    print(f"   • Our Status: {c['status']}")
