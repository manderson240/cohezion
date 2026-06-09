#!/usr/bin/env python3
"""
GitHub Scout - Asynchronous Workforce Terminal.

Polls GitHub for issues with 'agent-task' labels and triggers agent journeys.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("github-scout")

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent.parent.parent.parent
PROCESSED_FILE = PROJECT_ROOT / ".github_scout_processed.json"

# We use the internal engine directly to avoid the overhead of MCP loop
from cohezion.mcp.servers.github.server import get_service  # noqa: E402
from cohezion.reliability.heartbeat import update_heartbeat  # noqa: E402
from cohezion.universe.engine import UniverseSimulationEngine  # noqa: E402


def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f, indent=2)


async def poll_github():
    """Main polling loop."""
    # Configuration - In production these would be env vars
    OWNER = os.getenv("GITHUB_OWNER", "manderson240")
    REPO = os.getenv("GITHUB_REPO", "cohezion")
    LABEL = "agent-task"

    logger.info(f"Starting GitHub Scout for {OWNER}/{REPO} (label: {LABEL})")

    processed = load_processed()
    engine = UniverseSimulationEngine()
    github = get_service()

    while True:
        update_heartbeat("github-scout")
        try:
            logger.debug("Checking for new tasks...")
            issues_result = await github.list_issues(OWNER, REPO, labels=[LABEL])

            for issue in issues_result:
                issue_id = f"{OWNER}/{REPO}#{issue['number']}"

                if issue_id in processed:
                    continue

                logger.info(f"🚀 New Agent Task detected: {issue['title']} ({issue_id})")

                # 1. Trigger Journey
                # We link the issue ID in the initial context
                journey = await engine.start_journey(
                    agent_name="GitHubScout",
                    intent=issue["title"],
                    context={
                        "source": "github_issue",
                        "github_issue_id": issue["number"],
                        "github_issue_ref": issue_id,
                        "github_issue_url": issue["url"],
                        "issue_body": issue.get("body", ""),
                    },
                )

                logger.info(f"  Journey started: {journey.journey_id}")

                # 2. Acknowledge on GitHub
                await github.create_issue_comment(
                    OWNER,
                    REPO,
                    issue["number"],
                    f"🤖 **Cohezion Agent Dispatched**\n\n"
                    f"Task received and journey initiated.\n"
                    f"- **Journey ID**: `{journey.journey_id}`\n"
                    f"- **Status**: `In Progress`\n\n"
                    f"Results will be reported here upon completion.",
                )

                processed.add(issue_id)
                save_processed(processed)

        except Exception as e:
            logger.error(f"Error in polling loop: {e}")

        # Interval (e.g., 5 minutes)
        await asyncio.sleep(300)


if __name__ == "__main__":
    try:
        asyncio.run(poll_github())
    except KeyboardInterrupt:
        logger.info("GitHub Scout stopped.")
