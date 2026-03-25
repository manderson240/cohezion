import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path(__name__).parent / "src"))

from cohezion.swarm.agents.analyst import AnalystAgent

from cohezion.core.credit_manager import get_credit_manager
from cohezion.swarm.swarm_types import Perspective, SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("DegradationVerification")

    # 1. Test Model Fallback (CREDITS)
    credit_manager = get_credit_manager()
    agent_id = "AnalystAgent"

    # Set balance low: 10 credits
    # claude-opus-4.5 costs 20.
    # phi3:mini costs 1.
    credit_manager.deduct(agent_id, credit_manager.get_balance(agent_id) - 10)
    print(f"Current Balance for {agent_id}: {credit_manager.get_balance(agent_id)}")

    config = SwarmConfig()
    # Explicitly request a model we can't afford
    agent = AnalystAgent(Perspective.TECHNICAL, config=config)
    agent.model_name = "claude-opus-4.5"

    print("\n--- Testing Model Fallback (Insufficient Credits) ---")
    await agent.analyze("Explain quantum entanglement.")

    # 2. Test Degraded Mode (PROMPT PRUNING)
    print("\n--- Testing Degraded Mode (Prompt Pruning) ---")
    config.degraded_mode = True
    long_prompt = "A" * 2000  # Very long prompt

    await agent.analyze(long_prompt)

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
