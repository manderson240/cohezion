import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.agents.memory_agent import MemoryAgent

from cohezion.swarm.swarm_types import Perspective, SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("MemoryVerification")

    config = SwarmConfig()
    analyst = AnalystAgent(Perspective.TECHNICAL, config=config)
    memory_agent = MemoryAgent(config=config)

    # 1. Seed a specific memory
    print("\n--- Seeding Mission Memory ---")
    mission_context = "Mission 'Ghost Sparrow' concluded in December 2025. Key finding: The Fractal Toroidal interface requires a 0.52 stability offset to prevent brane-drift."
    print(f"Storing: {mission_context}")
    # Call ollama via analyst to get it into the persistent memory (via BaseAgent's auto-persistence)
    await analyst._call_ollama(f"Summarize this mission result: {mission_context}", ignore_cache=True)

    # 2. Retrieve via MemoryAgent
    print("\n--- Testing Recursive Recall ---")
    query = "What do we know about the Ghost Sparrow mission and stability offsets?"

    # First, test raw context retrieval
    context = await memory_agent.get_relevant_context(query)
    print(f"\nRetrieved Context:\n{context}")

    # Second, test synthesis
    synthesis = await memory_agent.process(query)
    print(f"\nSynthesized Memory:\n{synthesis}")

    await analyst.close()
    await memory_agent.close()


if __name__ == "__main__":
    asyncio.run(main())
