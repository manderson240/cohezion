#!/usr/bin/env python3
"""
Hourly Job: Autonomic Research Scout
Showcases SKILL: AUTONOMIC_RESEARCH_PRIME
Delegate: qwen3-coder-next:latest (Trend Sensing)
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import trackio

from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ResearchScout")


async def main():
    logger.info("🛰️ Starting Hourly Research Scout (Hugging Face / arXiv)...")

    # Initialize Trackio (Local only)
    trackio.init(project="cohezion-core")

    # 1. Sensing: Delegate the SEARCH to the Smart Router
    # We use the prompt to trigger 'paper_search' or 'hub_repo_search' via the agent
    client = get_compound_client()

    prompt = """
    You are an AUTONOMIC_RESEARCH_PRIME specialist.
    Perform a search on Hugging Face and arXiv for the latest developments in:
    - 'KV Cache Compaction for Agentic RAG'
    - 'Propellant-free thrust and vacuum engineering'
    
    Instruction:
    - Identify the top 3 most relevant artifacts (papers or models).
    - Summarize their 'Core Mechanism'.
    - Calculate a 'Compound Impact Score' (CIS) from 0.0 to 1.0.
    - Format as a Markdown list.
    """

    response = await client.generate(prompt, task_type="analysis")

    # 2. Manifestation: Save to Research Feed
    feed_file = Path("src/cohezion/knowledge_graph/RESEARCH_FEED.md")
    feed_file.parent.mkdir(parents=True, exist_ok=True)

    if not feed_file.exists():
        feed_file.write_text("# Cohezion Autonomic Research Feed\n\n")

    with open(feed_file, "a") as f:
        f.write(f"\n## Feed Update {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(response)
        f.write("\n---\n")

    # 3. Alerting: If a high-score breakthrough is found, fire an alert
    if "CIS: 0.8" in response or "CIS: 0.9" in response or "CIS: 1.0" in response:
        trackio.alert(
            title="HIGH-IMPACT BREAKTHROUGH",
            text="Research Scout identified a breakthrough with CIS > 0.8. Check RESEARCH_FEED.md.",
            level=trackio.AlertLevel.INFO,
        )

    logger.info(f"✅ Research Scout complete. Feed updated: {feed_file}")
    trackio.finish()


if __name__ == "__main__":
    asyncio.run(main())
