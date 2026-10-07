"""GET /compound/health carries the live executor's degradation (CB6) and oracle (HO4) health.

The routes/compound.py extraction dropped both fields, so the endpoint always reported None
even when an executor was running. The prior revision fails the first test.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from cohezion.api import app
from cohezion.compound.executor_factory import ExecutorFactory


class _Oracle:
    def to_health_dict(self) -> dict:
        return {"regime": "stable", "tier": "npu"}


@pytest.fixture
def live_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = SimpleNamespace(
        get_health=lambda: {"coherence": True, "latency": None},
        _skill_refiner=SimpleNamespace(_health_oracle=_Oracle()),
    )
    monkeypatch.setattr(ExecutorFactory, "_instance", executor)


async def _health() -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/compound/health")
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_live_executor_health_is_reported(live_executor: None) -> None:
    body = await _health()
    assert body["degradation_health"] == {"coherence": True, "latency": None}
    assert body["oracle_health"] == {"regime": "stable", "tier": "npu"}


@pytest.mark.asyncio
async def test_no_executor_still_serves_base_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ExecutorFactory, "_instance", None)
    body = await _health()
    assert body["degradation_health"] is None and body["oracle_health"] is None
    assert "total_executions" in body


@pytest.mark.asyncio
async def test_failing_enrichment_does_not_break_the_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> dict:
        raise RuntimeError("detector offline")

    monkeypatch.setattr(ExecutorFactory, "_instance", SimpleNamespace(get_health=_boom))
    body = await _health()
    assert body["degradation_health"] is None
