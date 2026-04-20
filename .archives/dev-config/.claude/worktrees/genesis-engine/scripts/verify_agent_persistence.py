import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.swarm_types import Perspective, SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("Verification")

    config = SwarmConfig()
    agent = AnalystAgent(Perspective.TECHNICAL, config=config)

    query = "Explain the importance of non-blocking I/O in async systems."

    print(f"\n--- Running Verification for Query: '{query}' ---\n")

    for i in range(1, 4):
        print(f"Call {i}...")
        thought = await agent.process(query)

        print(f"  - Content Length: {len(thought.content)}")
        print(f"  - Embedding: {'Present' if thought.embedding else 'Missing'}")
        print(f"  - Persistence ID: {thought.persistence_id}")
        print(f"  - Frequency Count: {thought.frequency_count}")
        print("-" * 20)

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
