import asyncio
import os
import sys
from unittest.mock import MagicMock


# Setup paths
sys.path.append(os.path.abspath("src"))

from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig


# Mocks
# Prevent ResourceMonitor from killing the test due to high VRAM (likely from other background tasks)
sys.modules["cohezion.reliability.monitor"] = MagicMock()


class MockAgent(BaseAgent):
    async def process(self, *args, **kwargs):
        pass


async def test_base_agent_semantic_cache():
    print("🧪 Testing BaseAgent Integration...")

    # 1. Setup Agent
    cfg = SwarmConfig()
    agent = MockAgent(model_name="mock-model", config=cfg)

    # Manually inject the semantic cache to spy on it?
    # Or just run _call_ollama and see log output/return value?

    # We will populate the cache first using the internal method via a backdoor or direct DB
    from cohezion.caching.semantic_cache import SemanticCache

    sc = SemanticCache()
    await sc.connect()

    # Clear cache for this test? (Assuming local table is persistent)
    # We'll use a unique query to avoid collision
    unique_q = f"What is the semantic meaning of Life? {os.urandom(4).hex()}"
    unique_r = "42, but primarily the 0.5 stability point."

    print(f"Phase A: Caching unique query: {unique_q}")
    await sc.set(unique_q, unique_r)

    # 2. Call Agent with Similar Query
    similar_q = unique_q.replace("?", " please?")
    print(f"Phase B: Asking agent similar query: {similar_q}")

    # Mock user creds/manager to avoid blocks
    agent._credit_manager.can_afford = MagicMock(return_value=True)

    # Mock async client.post
    async def mock_post(*args, **kwargs):
        raise RuntimeError("Should not be called if cache hits!")

    agent.client.post = mock_post

    response = await agent._call_ollama(similar_q, ignore_cache=False)

    print(f"Response: {response}")
    print(f"Persistence ID: {response.persistence_id}")

    if response == unique_r and response.persistence_id == "semantic_hit":
        print("✅ SUCCESS: Agent returned semantic cache hit!")
    else:
        print("❌ FAILURE: Agent did not use semantic cache.")


if __name__ == "__main__":
    asyncio.run(test_base_agent_semantic_cache())
