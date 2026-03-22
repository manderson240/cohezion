import asyncio
import logging

from cohezion.agents.base import BaseAgent
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.swarm.swarm_types import SwarmConfig


# Configure logging to see the persistence flushes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAgent(BaseAgent):
    async def process(self, query: str):
        # Trigger an Ollama call (mocked or real depending on environment)
        # We'll use _call_ollama directly to test the hook
        return await self._call_ollama(prompt=query, task_type="reasoning")


async def verify_loop():
    print("--- 1. Initializing Test Agent ---")
    config = SwarmConfig(max_refinement_rounds=1)
    agent = TestAgent(model_name="phi3:mini", config=config)

    print("\n--- 2. Checking System Dilation ---")
    monitor = get_resource_monitor()
    dilation = monitor.get_dilation_factor()
    print(f"Current Dilation Factor: {dilation:.2f}")

    if dilation < 0.3:
        print("WARNING: System is too dilated. Persistence will be skipped naturally.")

    print("\n--- 3. Triggering Agent Mission ---")
    query = "Explain the HIHO stability protocol in 12D state vectors."
    response = await agent.process(query)
    print(f"Agent Response: {response[:100]}...")

    print("\n--- 4. Waiting for Accumulator Flush (5s) ---")
    # Accumulator has a 5s default flush interval
    await asyncio.sleep(7)

    print("\n--- 5. Verification Complete ---")
    print("Check logs for 'Flushing X experiences' and 'Persisted mission journey'.")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(verify_loop())
