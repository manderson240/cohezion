#!/usr/bin/env python3
"""
Research Task Driver
Usage: python research_task.py --topic "Topic" --context "Context/URL"
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from cohezion.swarm.agents.lab_agent import LabAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research_task")


async def main():
    parser = argparse.ArgumentParser(description="Run directed AI Lab research.")
    parser.add_argument("--topic", type=str, required=True, help="Research topic")
    parser.add_argument("--context", type=str, required=True, help="Context or URL content")

    args = parser.parse_args()

    logger.info(f"Initializing Lab Agent for topic: {args.topic}")
    agent = LabAgent()

    logger.info("Starting Research Cycle...")
    discovery = await agent.research_specific_topic(args.topic, args.context)

    if discovery:
        print("\n" + "=" * 80)
        print("RESEARCH DISCOVERY")
        print("=" * 80)
        print(f"ID: {discovery.id}")
        print(f"Alignment: {discovery.metadata.get('anthropic_alignment', 'N/A')}")
        print("-" * 40)
        print(discovery.content)
        print("=" * 80 + "\n")
    else:
        logger.error("Research produced no discovery node.")


if __name__ == "__main__":
    asyncio.run(main())
