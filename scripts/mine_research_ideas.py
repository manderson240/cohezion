import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.swarm.agents.inbox_miner import InboxMiner
from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("EmailResearch")

    # Ensure environment variables are loaded if not already
    from dotenv import load_dotenv

    load_dotenv()

    SwarmConfig()
    miner = InboxMiner(model_name="mistral:7b")  # Use mistral for mining

    print("\n--- Mining Inbox for Cohezion Research Ideas ---")
    tasks = await miner.mine_history(limit=20)

    print(f"\nMined {len(tasks)} Research Ideas:")
    for i, task in enumerate(tasks):
        print(f"{i + 1}. {task['task_title']}")
        print(f"   Subject: {task['original_subject']}")
        print(f"   Date: {task['timestamp']}\n")

    await miner.close()


if __name__ == "__main__":
    asyncio.run(main())
