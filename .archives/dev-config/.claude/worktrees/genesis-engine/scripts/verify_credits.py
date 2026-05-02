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
    logging.getLogger("CreditVerification")

    config = SwarmConfig()
    credit_manager = get_credit_manager()

    # 1. Check Initial Balance
    agent_id = "AnalystAgent"
    balance = credit_manager.get_balance(agent_id)
    print(f"Initial Balance for {agent_id}: {balance}")

    agent = AnalystAgent(Perspective.TECHNICAL, config=config)

    # 2. Run a task and check deduction
    print("\n--- Running Task (Mistral:7b, Cost: 3) ---")
    await agent._call_ollama("What is the capital of France?")

    new_balance = credit_manager.get_balance(agent_id)
    print(f"Post-task Balance: {new_balance}")

    # 3. Simulate Bankruptcy
    print("\n--- Simulating Credit Bankruptcy ---")
    credit_manager.deduct(agent_id, new_balance)  # Set to 0
    print(f"Wiped Balance: {credit_manager.get_balance(agent_id)}")

    can_afford = credit_manager.can_afford(agent_id, "mistral:7b")
    print(f"Can afford mistral:7b? {can_afford}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
