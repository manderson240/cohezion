"""Adversarial tests for the ResourceMonitor concurrency guard.

These tests exercise the monitor's semaphore and backpressure logic DIRECTLY.
The previous incarnation routed through BaseAgent._call_ollama and was
unfixable: the LLM call path goes through LOCAL_ROUTER, not httpx, so the
`httpx.AsyncClient.post` patch never intercepted the real call and the tests
hung on a live Ollama round-trip under a 20-agent flood. It also left the
heartbeat task running, which under mocked-95% vitals triggers
emergency_shutdown — a subprocess fan-out to curl/ollama that blocks for
seconds.

Scope is now what the docstrings always promised: does the semaphore actually
cap concurrency, and does pressure-gated backpressure fire when vitals are
high. Both are pure monitor concerns, so we mock at the method boundary.
"""

import asyncio
import contextlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.reliability.monitor import get_resource_monitor


@pytest.fixture
def quiet_monitor():
    """Yield the monitor singleton with its heartbeat task suppressed.


@pytest.fixture(autouse=True)
async def stop_monitor_after_test():
    """Cancel the ResourceMonitor heartbeat task after each anyio test.

    ResourceMonitor.__init__ calls loop.create_task(_heartbeat_loop()) when
    an event loop is running. Without this teardown the infinite heartbeat task
    prevents anyio from shutting down the event loop, hanging the test suite.
    """
    yield
    monitor = get_resource_monitor()
    await monitor.stop()


@pytest.mark.anyio
async def test_adversarial_flood():
    """
    Flood Attack: Spawns many agents to ensure semaphore never exceeds limit.
    The heartbeat's emergency_shutdown path fires real curl subprocesses under
    extreme-vitals mocks, which is why the previous version of these tests
    hung indefinitely. Disabling the heartbeat keeps the test to the seam we
    actually want to exercise (wait_for_capacity / release_capacity).
    """
    monitor = get_resource_monitor()
    original_max = monitor.max_concurrency
    original_sem = monitor.semaphore
    original_active = monitor.active_calls
    original_running = monitor._running

    # Suppress the heartbeat loop for the duration of the test.
    monitor._running = False
    heartbeat = getattr(monitor, "_heartbeat_task", None)
    if heartbeat is not None and not heartbeat.done():
        heartbeat.cancel()

    yield monitor

    # Restore
    monitor.max_concurrency = original_max
    monitor.semaphore = original_sem
    monitor.active_calls = original_active
    monitor._running = original_running


@pytest.mark.asyncio
async def test_adversarial_flood(quiet_monitor):
    """Flood attack: 20 concurrent acquirers must never exceed max_concurrency=4.

    Observes peak active_calls during the flood and asserts the semaphore cap.
    """
    monitor = quiet_monitor
    monitor.max_concurrency = 4
    monitor.semaphore = asyncio.Semaphore(4)
    monitor.active_calls = 0

    peak_active = 0

    # Green vitals so we don't hit the throttle path.
    def _green_vitals():
        return {"cpu_percent": 10.0, "memory_percent": 10.0, "vram_percent": 1.0}

    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"response": "Mocked stability response"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
    monitor.get_vitals = _green_vitals

    async def _hold_slot(hold_seconds: float):
        nonlocal peak_active
        await monitor.wait_for_capacity()
        try:
            peak_active = max(peak_active, monitor.active_calls)
            await asyncio.sleep(hold_seconds)
        finally:
            monitor.release_capacity()

    tasks = [asyncio.create_task(_hold_slot(0.05)) for _ in range(20)]
    await asyncio.gather(*tasks)

    assert peak_active <= 4, (
        f"Semaphore broken: observed {peak_active} concurrent holders, max should be 4"
    )
    assert monitor.active_calls == 0, (
        f"release_capacity leak: active_calls={monitor.active_calls} after flood drained"
    )


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_resource_backpressure(quiet_monitor, monkeypatch):
    """Vitals pressure triggers the throttle sleep in wait_for_capacity.

    We record sleep durations and replace asyncio.sleep with a no-op to keep
    the test fast while still asserting the throttle branch ran.
    """
    monitor = quiet_monitor

    # Force extreme vitals at the method boundary (skipping psutil entirely).
    def _red_vitals():
        return {"cpu_percent": 95.0, "memory_percent": 95.0, "vram_percent": 50.0}

    monitor.get_vitals = _red_vitals

    sleep_durations: list[float] = []
    real_sleep = asyncio.sleep

    async def _recording_sleep(duration, *args, **kwargs):
        sleep_durations.append(duration)
        return await real_sleep(0, *args, **kwargs)

    monkeypatch.setattr(asyncio, "sleep", _recording_sleep)

    start = time.perf_counter()
    await monitor.wait_for_capacity()
    elapsed = time.perf_counter() - start
    monitor.release_capacity()

    # The throttle branch fires a 10s sleep; our patch compresses it.
    assert any(d >= 5.0 for d in sleep_durations), (
        f"Expected throttle sleep >= 5s under extreme vitals, got sleeps={sleep_durations}"
    )
    assert monitor.throttled is True, "Monitor should flag throttled=True under extreme vitals"
    assert elapsed < 5.0, f"Test should complete quickly via sleep patch, took {elapsed:.2f}s"


@pytest.mark.asyncio
@pytest.mark.skipif(True, reason="Requires live Ollama with mistral:7b")
async def test_real_llm_load_controlled():
    """Optional: 4 concurrent real LLM calls to verify TTM stability.

    Kept for manual verification against a live Ollama instance; skipped in CI.
    """
    from cohezion.agents.base import BaseAgent

    class MockAgent(BaseAgent):
        async def process(self, query: str) -> str:
            return await self._call_ollama(query, ignore_cache=True)

    agents = [MockAgent(model_name="mistral:7b") for _ in range(4)]
    tasks = [agent.process("Briefly explain the 0.5 Coherence Rule.") for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Cancel any leftover tasks defensively before asserting.
    for t in tasks:
        if not t.done():
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await t
    assert all(not isinstance(r, Exception) for r in results)
