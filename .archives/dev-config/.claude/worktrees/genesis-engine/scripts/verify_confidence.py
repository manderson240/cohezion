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
    logging.getLogger("ConfidenceVerification")

    config = SwarmConfig()
    analyst = AnalystAgent(Perspective.TECHNICAL, config=config)

    # 1. High Certainty Question
    print("\n--- Testing High Certainty (Fact) ---")
    q_high = "What is the atomic number of Gold?"
    resp_high = await analyst.analyze(q_high, ignore_cache=True)
    print(f"Query: {q_high}")
    print(f"Phi Score: {resp_high.phi_score:.2f}")
    print(f"Confidence: {resp_high.confidence:.2f}")

    # 2. Low Certainty / Speculative Question
    print("\n--- Testing Low Certainty (Speculation) ---")
    q_low = "What will be the exact stock price of Apple (AAPL) on December 12, 2030, at 11:34 AM UTC?"
    resp_low = await analyst.analyze(q_low, ignore_cache=True)
    print(f"Query: {q_low}")
    print(f"Phi Score: {resp_low.phi_score:.2f}")
    print(f"Confidence: {resp_low.confidence:.2f}")

    # Validation logic
    if resp_high.confidence > resp_low.confidence:
        print(
            f"\n✅ PASS: Calibration delta detected (Delta: {resp_high.confidence - resp_low.confidence:.2f})"
        )
    else:
        print("\n❌ FAIL: No significant calibration delta detected.")

    await analyst.close()


if __name__ == "__main__":
    asyncio.run(main())
