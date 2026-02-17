import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.librarian_agent import LibrarianAgent
from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("LibrarianVerification")

    config = SwarmConfig()
    librarian = LibrarianAgent(config=config)

    print("\n--- Running Librarian Documentation Audit ---")
    report = await librarian.process("audit")
    print(f"Audit Report:\n{report}")

    await librarian.close()


if __name__ == "__main__":
    asyncio.run(main())
