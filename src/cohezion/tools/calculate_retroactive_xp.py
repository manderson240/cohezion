#!/usr/bin/env python3
"""Retroactive XP Calculator for Cohezion.

Parses git history and journey history to calculate XP for existing contributions.

Usage:
    python -m cohezion.tools.calculate_retroactive_xp --dry-run
    python -m cohezion.tools.calculate_retroactive_xp --since=2025-01-01

This will:
1. Parse git commit history (with timeout)
2. Query journey history from SurrealDB
3. Award retroactive XP to all agents
4. Generate a report of total XP awarded
"""

import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("retroactive_xp")


def get_git_history(
    since: str | None = None, timeout: int = 30
) -> list[dict[str, Any]]:
    """Parse git log for commit history with timeout."""
    cmd = ["git", "log", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]

    if since:
        cmd.append(f"--since={since}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=timeout,
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append(
                        {
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "subject": parts[3],
                        }
                    )

        return commits

    except subprocess.TimeoutExpired:
        logger.warning("Git history parsing timed out after 30 seconds")
        return []
    except Exception as e:
        logger.error(f"Failed to parse git history: {e}")
        return []


async def get_journey_history() -> list[dict[str, Any]]:
    """Query journey history from SurrealDB."""
    try:
        from cohezion.core.persistence.surreal_client import SurrealClient

        db = SurrealClient()
        await db.connect()

        result = await db.query(
            "SELECT * FROM universe_journey WHERE status = 'completed' ORDER BY created_at DESC LIMIT 100"
        )

        journeys = []
        for row in result:
            journeys.append(
                {
                    "id": row.get("id"),
                    "agent_name": row.get("agent_name"),
                    "phi_score": row.get("final_phi_score", 0.5),
                }
            )

        await db.close()
        return journeys

    except Exception as e:
        logger.warning(f"Could not query journey history: {e}")
        return []


async def calculate_retroactive_xp(
    since: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Calculate and award retroactive XP."""
    logger.info("=" * 60)
    logger.info("🚀 RETROACTIVE XP CALCULATOR")
    logger.info("=" * 60)

    if dry_run:
        logger.info("⚠️  DRY RUN - No XP will be awarded")

    logger.info("\n📥 Parsing git history (with timeout)...")
    git_history = get_git_history(since, timeout=30)
    logger.info(f"   Found {len(git_history)} commits")

    logger.info("\n📊 Querying journey history...")
    journey_history = await get_journey_history()
    logger.info(f"   Found {len(journey_history)} completed journeys")

    from cohezion.rewards.system import RewardSystem

    rewards = RewardSystem()

    author_commits: dict[str, list[dict[str, Any]]] = {}
    for commit in git_history:
        author = commit["author"]
        author_commits.setdefault(author, []).append(commit)

    agent_journeys: dict[str, list[dict[str, Any]]] = {}
    for journey in journey_history:
        agent = journey.get("agent_name", "Unknown")
        agent_journeys.setdefault(agent, []).append(journey)

    report = {
        "calculated_at": datetime.now().isoformat(),
        "total_xp_awarded": 0,
        "by_author": {},
    }

    all_agents = set(author_commits.keys()) | set(agent_journeys.keys())

    for agent in sorted(all_agents):
        commits = author_commits.get(agent, [])
        journeys = agent_journeys.get(agent, [])

        if not dry_run:
            retro_xp = rewards.calculate_retroactive_xp(agent, commits, journeys)
        else:
            retro_xp = len(commits) * 10 + len(journeys) * 25

        report["by_author"][agent] = {
            "commits": len(commits),
            "journeys": len(journeys),
            "xp": retro_xp,
        }
        report["total_xp_awarded"] += retro_xp

        logger.info(
            f"   {agent}: {retro_xp} XP ({len(commits)} commits, {len(journeys)} journeys)"
        )

    logger.info("\n" + "=" * 60)
    logger.info(f"📋 TOTAL XP: {report['total_xp_awarded']}")
    logger.info("=" * 60)

    return report


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Calculate retroactive XP for existing contributions"
    )
    parser.add_argument("--since", help="Filter commits since date")
    parser.add_argument(
        "--dry-run", action="store_true", help="Calculate without awarding"
    )

    args = parser.parse_args()

    await calculate_retroactive_xp(since=args.since, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
