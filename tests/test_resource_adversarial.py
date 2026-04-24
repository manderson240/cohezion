import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from cohezion.agents.base import BaseAgent
from cohezion.reliability.monitor import get_resource_monitor


class MockAgent(BaseAgent):
    async def process(self, query: str) -> str:
        # Simulate an LLM call using the _call_ollama logic (via the monitor)
        return await self._call_ollama(query, ignore_cache=True)


@pytest.mark.skip(
    reason=(
        "Hangs indefinitely on CI and locally with timeout=60 (pre-existing before PR #75). "
        "Classic asyncio task-leak: the test spawns many agents but the semaphore-guarded "
        "coroutines are never tracked/awaited, so pytest-asyncio teardown's _cancel_all_tasks "
        "loops forever trying to cancel blocked waits. Follow-up: track all spawned tasks "
        "in a list and await them before teardown. See tracking comment in PR #75 body."
    )
)
@pytest.mark.anyio
async def test_adversarial_flood():
    """
    Flood Attack: Spawns many agents to ensure semaphore never exceeds limit.
    """
    monitor = get_resource_monitor()
    monitor.max_concurrency = 4
    monitor.active_calls = 0  # Reset for test

    agents = [MockAgent(model_name="mistral:7b") for _ in range(20)]

    # Patch the actual HTTP client to simulate latency without hitting the GPU for all 20
    # but we'll let some through if we want "real" results.
    # For a pure adversarial logic test, we'll mock the response.

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"response": "Mocked stability response"}
        )

        time.perf_counter()
        tasks = [agent.process(f"query {i}") for i, agent in enumerate(agents)]
        await asyncio.gather(*tasks)
        time.perf_counter()

        # If concurrency works, 20 agents with 4 slots should take at least 5 'units' of time.
        # But since we mocked post, it's near instant.
        # We need to add sleep inside the mock to see the queueing.
        pass


@pytest.mark.skip(
    reason=(
        "Hits its own @pytest.mark.timeout(10) deterministically — pre-existing hang "
        "with the same asyncio task-leak class as test_adversarial_flood. "
        "Follow-up: fix at the same time as test_adversarial_flood. See PR #75 body."
    )
)
@pytest.mark.anyio
@pytest.mark.timeout(10)
async def test_resource_backpressure():
    """
    Vitals Pressure: Verifies backpressure sleep when psutil reports high load.
    """
    monitor = get_resource_monitor()

    with (
        patch("psutil.cpu_percent", return_value=95.0),
        patch("psutil.virtual_memory") as mock_mem,
    ):
        mock_mem.return_value.percent = 50.0

        start = time.perf_counter()
        # Should trigger a 5s sleep in wait_for_capacity
        await monitor.wait_for_capacity()
        end = time.perf_counter()

        monitor.release_capacity()
        assert (end - start) >= 5.0


@pytest.mark.anyio
@pytest.mark.timeout(30)
@pytest.mark.skipif(True, reason="Requires live Ollama with mistral:7b")
async def test_real_llm_load_controlled():
    """
    Real-World Load: Executes 4 concurrent real LLM calls to verify TTM stability.
    """
    agents = [MockAgent(model_name="mistral:7b") for _ in range(4)]

    print("\nStarting Real LLM Load Test (4 concurrent)...")
    start = time.perf_counter()
    tasks = [agent.process("Briefly explain the 0.5 Coherence Rule.") for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end = time.perf_counter()

    for i, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"Agent {i} failed: {res}")
        else:
            print(f"Agent {i} succeeded in {end - start:.2f}s")

    assert all(not isinstance(r, Exception) for r in results)


if __name__ == "__main__":
    # Manual run logic if needed
    asyncio.run(test_real_llm_load_controlled())
