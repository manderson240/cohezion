#!/usr/bin/env python3
"""Retroactive XP Calculator for Cohezion.

Parses git history and journey history to calculate XP for existing contributions.
Run this once to recognize all historical work:

    uv run python -m cohezion.tools.calculate_retroactive_xp

This will:
1. Parse git commit history
2. Query journey history from SurrealDB
3. Award retroactive XP to all agents
4. Generate a report of total XP awarded
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.rewards.system import RewardSystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("retroactive_xp")


def get_git_history(since: str | None = None) -> list[dict[str, Any]]:
    """Parse git log for commit history.

    Args:
        since: Optional date filter (e.g., '2024-01-01')

    Returns:
        List of commit dictionaries with metadata
    """
    cmd = [
        "git",
        "log",
        "--pretty=format:%H|%an|%ad|%s|%f",
        "--date=iso",
    ]

    if since:
        cmd.append(f"--since={since}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    # Get file change stats for this commit
                    commit_hash = parts[0]
                    stats = get_commit_stats(commit_hash)

                    commits.append(
                        {
                            "hash": commit_hash,
                            "author": parts[1],
                            "date": parts[2],
                            "subject": parts[3],
                            "files_changed": stats["files_changed"],
                            "insertions": stats["insertions"],
                            "deletions": stats["deletions"],
                        }
                    )

        return commits

    except Exception as e:
        logger.error(f"Failed to parse git history: {e}")
        return []


def get_commit_stats(commit_hash: str) -> dict[str, int]:
    """Get file change statistics for a commit."""
    try:
        result = subprocess.run(
            ["git", "show", "--stat", "--format=", commit_hash],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        files_changed = 0
        insertions = 0
        deletions = 0

        for line in result.stdout.split("\n"):
            if "changed," in line:
                parts = line.split()
                try:
                    files_changed = int(parts[0])
                    # Look for insertion/deletion counts
                    if "insertion" in line:
                        insertions = int(parts[3]) if len(parts) > 3 else 0
                    elif "deletion" in line:
                        deletions = int(parts[3]) if len(parts) > 3 else 0
                except (ValueError, IndexError):
                    pass
            elif line.endswith(")"):
                # Line like "10 files changed, 234 insertions(+), 5 deletions(-)"
                if "insertion" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "insertion":
                            insertions = int(parts[i - 2].replace(",", ""))
                        elif part == "deletion":
                            deletions = int(parts[i - 2].replace(",", ""))

        return {
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
        }

    except Exception:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}


async def get_journey_history() -> list[dict[str, Any]]:
    """Query journey history from SurrealDB."""
    try:
        from cohezion.db.surreal_client import SurrealClient

        db = SurrealClient()
        await db.connect()

        # Query completed journeys
        result = await db.query(
            "SELECT * FROM universe_journey WHERE status = 'completed' ORDER BY created_at DESC"
        )

        journeys = []
        for row in result:
            journeys.append(
                {
                    "id": row.get("id"),
                    "agent_name": row.get("agent_name"),
                    "intent": row.get("intent"),
                    "phi_score": row.get("final_phi_score", 0.5),
                    "created_at": row.get("created_at"),
                    "completed_at": row.get("completed_at"),
                }
            )

        await db.close()
        return journeys

    except Exception as e:
        logger.warning(f"Could not query journey history: {e}")
        return []


async def calculate_all_retroactive_xp(
    since: str | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """Calculate and award retroactive XP for all historical contributions.

    Args:
        since: Optional date filter for git history
        dry_run: If True, calculate but don't award XP

    Returns:
        Report of XP awarded
    """
    logger.info("=" * 60)
    logger.info("🚀 RETROACTIVE XP CALCULATOR")
    logger.info("=" * 60)

    if dry_run:
        logger.info("⚠️  DRY RUN - No XP will be awarded")

    # 1. Parse git history
    logger.info("\n📥 Step 1: Parsing git history...")
    git_history = get_git_history(since)
    logger.info(f"   Found {len(git_history)} commits")

    # Group commits by author
    author_commits: dict[str, list[dict[str, Any]]] = {}
    for commit in git_history:
        author = commit["author"]
        if author not in author_commits:
            author_commits[author] = []
        author_commits[author].append(commit)

    logger.info(f"   Authors: {', '.join(author_commits.keys())}")

    # 2. Get journey history
    logger.info("\n📊 Step 2: Querying journey history...")
    journey_history = await get_journey_history()
    logger.info(f"   Found {len(journey_history)} completed journeys")

    # Group journeys by agent
    agent_journeys: dict[str, list[dict[str, Any]]] = {}
    for journey in journey_history:
        agent = journey.get("agent_name", "Unknown")
        if agent not in agent_journeys:
            agent_journeys[agent] = []
        agent_journeys[agent].append(journey)

    # 3. Calculate and award XP
    logger.info("\n🏆 Step 3: Calculating retroactive XP...")

    rewards = RewardSystem()

    report = {
        "calculated_at": datetime.now().isoformat(),
        "since": since,
        "dry_run": dry_run,
        "authors_processed": len(author_commits),
        "agents_with_journeys": len(agent_journeys),
        "total_xp_awarded": 0,
        "by_author": {},
    }

    # Process git commits (by author)
    for author, commits in author_commits.items():
        if not dry_run:
            retro_xp = rewards.calculate_retroactive_xp(
                agent_id=author,
                git_history=commits,
                journey_history=agent_journeys.get(author, []),
            )
        else:
            # Calculate without awarding
            retro_xp = sum(
                10
                + (20 if c["files_changed"] > 5 else 0)
                + (15 if c["insertions"] > 100 else 0)
                for c in commits
            )

        report["by_author"][author] = {
            "commits": len(commits),
            "xp_from_commits": retro_xp,
            "journeys": len(agent_journeys.get(author, [])),
        }
        report["total_xp_awarded"] += retro_xp

        logger.info(f"   {author}: {retro_xp} XP ({len(commits)} commits)")

    # Process agents with journeys but no commits
    all_agents = set(author_commits.keys()) | set(agent_journeys.keys())
    for agent in all_agents:
        if agent not in author_commits and agent in agent_journeys:
            if not dry_run:
                retro_xp = rewards.calculate_retroactive_xp(
                    agent_id=agent,
                    git_history=[],
                    journey_history=agent_journeys[agent],
                )
            else:
                retro_xp = sum(
                    25
                    + (50 if j["phi_score"] > 0.8 else 0)
                    + (100 if j["phi_score"] > 0.95 else 0)
                    for j in agent_journeys[agent]
                )

            report["by_author"][agent] = {
                "commits": 0,
                "xp_from_commits": 0,
                "journeys": len(agent_journeys[agent]),
            }
            report["total_xp_awarded"] += retro_xp

            logger.info(
                f"   {agent}: {retro_xp} XP ({len(agent_journeys[agent])} journeys)"
            )

    # 4. Generate final report
    logger.info("\n" + "=" * 60)
    logger.info("📋 FINAL REPORT")
    logger.info("=" * 60)
    logger.info(f"   Authors processed: {report['authors_processed']}")
    logger.info(f"   Agents with journeys: {report['agents_with_journeys']}")
    logger.info(f"   Total XP awarded: {report['total_xp_awarded']}")

    # Show leaderboard
    logger.info("\n🏅 TOP CONTRIBUTORS:")
    sorted_authors = sorted(
        report["by_author"].items(),
        key=lambda x: report["by_author"][x[0]].get("xp_from_commits", 0),
        reverse=True,
    )[:10]

    for rank, (author, data) in enumerate(sorted_authors, 1):
        xp = data.get("xp_from_commits", 0)
        logger.info(f"   {rank}. {author}: {xp} XP")

    # Save report
    report_path = Path("data/rewards/retroactive_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"\n📄 Report saved to: {report_path}")

    return report


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Calculate retroactive XP for existing contributions"
    )
    parser.add_argument(
        "--since", help="Filter commits since date (e.g., '2024-01-01')"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Calculate XP without awarding it"
    )

    args = parser.parse_args()

    await calculate_all_retroactive_xp(
        since=args.since,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    asyncio.run(main())
