"""Unit tests for p0_resilience_mixins — P0 critical resilience features."""

from __future__ import annotations

import asyncio
import time

import pytest

from cohezion.inference.p0_resilience_mixins import HealthChecker, TimeoutMixin


# ── TimeoutMixin ──────────────────────────────────────────────────────────────


class ConcreteTimeoutable(TimeoutMixin):
    """Minimal concrete class to test TimeoutMixin."""

    pass


class TestTimeoutMixin:
    @pytest.mark.asyncio
    async def test_completes_within_timeout(self):
        """Fast coroutine returns normally."""
        t = ConcreteTimeoutable()

        async def fast_op():
            return "done"

        result = await t.with_timeout(fast_op(), timeout=5.0)
        assert result == "done"

    @pytest.mark.asyncio
    async def test_timeout_returns_error_dict(self):
        """Slow coroutine returns timeout error dict, not raises."""
        t = ConcreteTimeoutable()

        async def slow_op():
            await asyncio.sleep(10.0)
            return "never"

        result = await t.with_timeout(slow_op(), timeout=0.05)
        assert isinstance(result, dict), "Timeout must return dict, not raise"
        assert result.get("status") == "timeout"
        assert "timed out" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_timeout_calls_on_timeout_callback(self):
        """on_timeout callback is called when timeout fires."""
        t = ConcreteTimeoutable()
        callback_called = []

        async def slow_op():
            await asyncio.sleep(10.0)

        await t.with_timeout(
            slow_op(), timeout=0.05, on_timeout=lambda: callback_called.append(True)
        )
        assert len(callback_called) == 1, "on_timeout must be called exactly once"

    @pytest.mark.asyncio
    async def test_default_timeout_is_used_when_none(self):
        """Uses DEFAULT_TIMEOUT when timeout=None."""
        t = ConcreteTimeoutable()
        assert t.DEFAULT_TIMEOUT == 30.0

        async def fast_op():
            return 42

        result = await t.with_timeout(fast_op(), timeout=None)
        assert result == 42

    @pytest.mark.asyncio
    async def test_timeout_error_dict_has_timestamp(self):
        """Timeout error dict includes timestamp for debugging."""
        t = ConcreteTimeoutable()

        async def slow_op():
            await asyncio.sleep(10.0)

        before = time.time()
        result = await t.with_timeout(slow_op(), timeout=0.05)
        after = time.time()

        assert isinstance(result, dict)
        ts = result.get("timestamp", 0)
        assert before <= ts <= after + 1.0  # timestamp is within the call window


# ── HealthChecker ─────────────────────────────────────────────────────────────


class TestHealthChecker:
    def test_unknown_service_returns_unhealthy(self):
        """Checking an unregistered service returns unhealthy."""
        hc = HealthChecker(endpoints={"npu": "http://localhost:13306/v1/models"})
        result = hc.check_service("unknown-service")
        assert result["healthy"] is False
        assert "Unknown service" in result["error"]

    def test_unreachable_service_returns_unhealthy(self):
        """Service that refuses connection returns unhealthy with error."""
        hc = HealthChecker(endpoints={"test": "http://localhost:19999/v1/models"})
        result = hc.check_service("test", timeout=1.0)
        assert result["healthy"] is False
        assert "latency_ms" in result

    def test_check_all_returns_status_for_each_service(self):
        """check_all returns a result dict for every registered service."""
        hc = HealthChecker(
            endpoints={
                "npu": "http://localhost:19998/v1/models",
                "gpu": "http://localhost:19997/v1/models",
            }
        )
        results = hc.check_all()
        assert set(results.keys()) == {"npu", "gpu"}
        for svc, result in results.items():
            assert "healthy" in result, f"Missing 'healthy' for {svc}"

    def test_health_status_cache_updated(self):
        """health_status dict is updated after each check."""
        hc = HealthChecker(endpoints={"svc": "http://localhost:19996/v1/models"})
        assert "svc" not in hc.health_status
        hc.check_service("svc", timeout=0.5)
        assert "svc" in hc.health_status

    def test_live_npu_server_healthy(self):
        """NPU server on port 13306 should be up (N1 invariant) — when live infra is present.

        Skips where no NPU server is reachable (e.g. CI); asserts the latency SLA when it is.
        """
        hc = HealthChecker(endpoints={"npu": "http://localhost:13306/v1/models"})
        result = hc.check_service("npu", timeout=3.0)
        if not result["healthy"]:
            pytest.skip(f"NPU server not reachable — live infra unavailable: {result.get('error')}")
        assert result["latency_ms"] < 2000, "NPU health check must respond within 2s"
