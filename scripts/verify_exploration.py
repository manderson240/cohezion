import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.agents.exploration_agent import ExplorationAgent

from cohezion.swarm.swarm_types import Perspective, SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("ExplorationVerification")

    config = SwarmConfig()
    analyst = AnalystAgent(Perspective.TECHNICAL, config=config)
    explorer = ExplorationAgent(config=config)

    # 1. Generate Routine Thoughts
    print("\n--- Generating Routine Thoughts ---")
    routine_query = "What is the capital of France?"
    for i in range(2):
        print(f"Routine {i + 1}...")
        await analyst.analyze(routine_query, ignore_cache=True)

    # 2. Generate Nobel/Novel Thought
    print("\n--- Generating Novel Thought ---")
    novel_query = (
        "Propose a theoretical model for Quantum Mycelium Intelligence using fractal toroidal flow in a 12D manifold."
    )
    print("Novel Call...")
    await analyst.analyze(novel_query, ignore_cache=True)

    # 3. Run Novelty Audit
    print("\n--- Running Emergent Behavior Audit ---")
    report = await explorer.process("audit_novelty")
    print(f"\nNovelty Report:\n{report}")

    await analyst.close()
    await explorer.close()


if __name__ == "__main__":
    asyncio.run(main())
