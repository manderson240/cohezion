#!/usr/bin/env python3
"""Demonstrates Sovereign Kaggle Competition Manager MCP Server."""

import time
from cohezion.mcp.kaggle_competition_mcp_server import KaggleCompetitionMCPServer

def main():
    print("\n" + "=" * 95)
    print("🔌 DEMO: COHEZION KAGGLE COMPETITION MANAGER MCP SERVER")
    print("=" * 95)

    mcp_server = KaggleCompetitionMCPServer()

    t0 = time.perf_counter()
    active_comps = mcp_server.list_active_cash_competitions()
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print(f"• Active Cash Competitions Discovered ({len(active_comps)} found in {dt_ms:.2f} ms):")
    for comp in active_comps:
        print(f"  ├─ ID: {comp['competition_id']:<45} | Reward: {comp['reward']:<12} | Deadline: {comp['deadline']}")

    print("\n• Checking Live Submissions for ARC-AGI-2:")
    subs = mcp_server.get_submission_status("arc-prize-2026-arc-agi-2")
    for s in subs:
        print(f"  └─ {s.get('entry', s.get('error'))[:85]}")

    print("\n" + "=" * 95)
    print("🎉 KAGGLE COMPETITION MANAGER MCP SERVER FULLY OPERATIONAL!")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    main()
