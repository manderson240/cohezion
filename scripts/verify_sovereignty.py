import asyncio
import logging
import sys
from pathlib import Path
from cohezion.swarm.agents.sovereign_agent import SovereignAgent
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.core.local_registry import get_local_registry


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("SovereignVerify")

    # 1. Test Registry Directly
    registry = get_local_registry()
    print(f"\n--- 🛡️ Registry Test ---")
    print(f"Installed Models: {registry.available_models}")
    print(f"Capacity Check (>20GB): {registry.check_capacity()}")

    # 2. Test Sovereign Agent Fallback
    print(f"\n--- 🏰 Sovereign Agent Fallback Test ---")
    # Intentional Fake Model
    agent = SovereignAgent(config=SwarmConfig())
    agent.model_name = "gpt-4-turbo-fake"

    query = "What is the capital of France?"
    print(f"Requesting: {agent.model_name} (Fake)")

    # This call should trigger the _call_ollama override
    # and fallback to a local model without crashing
    response = await agent.process(query)

    print(f"Response Received: {response[:100]}...")

    if "Paris" in response:
        print("✅ PASS: Agent downgraded and responded successfully.")
    else:
        print("❌ FAIL: Response invalid.")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
