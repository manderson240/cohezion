import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.agents.pruning_agent import PruningAgent
from cohezion.swarm.swarm_types import SwarmConfig, Perspective

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("PruningVerification")

    config = SwarmConfig()
    analyst = AnalystAgent(Perspective.TECHNICAL, config=config)
    pruner = PruningAgent(config=config)

    # 1. Generate Redundant Thoughts
    print(f"\n--- Generating Redundant Thoughts ---")
    query = "Explain the 0.5 Coherence Rule in HIHO reality."
    for i in range(3):
        print(f"Call {i+1}: {query}...")
        await analyst.analyze(query, ignore_cache=True)

    # 2. Run Pruning Audit
    print(f"\n--- Running Knowledge Compression Audit ---")
    report = await pruner.process("compress")
    print(f"\nCompression Report:\n{report}")

    await analyst.close()
    await pruner.close()

if __name__ == "__main__":
    asyncio.run(main())
