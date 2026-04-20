import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.hypothesis_agent import HypothesisAgent
from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("HypothesisVerification")

    config = SwarmConfig()
    hypothesis_agent = HypothesisAgent(config=config)

    # Pure mathematical verifiable context
    context = (
        "Verify that a 768-dimensional vector where all elements are 0.0 has a Euclidean norm (L2) of exactly 0.0."
    )

    print("\n--- Testing Automated Hypothesis Testing ---")
    print(f"Context: {context}")

    # Run imagination and verification loop
    report = await hypothesis_agent.process(context)

    print("\n--- Hypothesis Report ---")
    print(report)

    # Simple validation: Check for "VERIFIED" in report
    if "VERIFIED" in report:
        print("\n✅ PASS: At least one conceptual hypothesis was empirically verified in the sandbox.")
    else:
        print("\n❌ FAIL: No hypotheses were verified (Check logs for sandbox failures).")

    await hypothesis_agent.close()


if __name__ == "__main__":
    asyncio.run(main())
