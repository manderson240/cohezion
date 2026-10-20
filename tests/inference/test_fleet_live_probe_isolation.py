"""route() tests in the gate must not depend on what the live router reports.

`fleet.route()` asks :13305 `/v1/models` which models are resident (`_get_lemonade_loaded_models`,
3 s timeout, 15 s module-level TTL cache) and skips candidates it does not list. Unit tests
register FAKE model ids, so their verdict depended on the router: answering -> every fake
candidate is "(not-loaded)" and the test fails; slow or down -> None, fail-open, test passes.
Measured 2026-09-21 at 22b6a1e46: two back-to-back runs of the same tree, 4 failures then 0
(test_fleet_recipe_gate x3, test_fleet_per_model_headroom x1).

tests/inference/conftest.py stubs the live probes to "unknown" for non-integration tests.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cohezion.inference import fleet as fleet_mod
from cohezion.inference.fleet import route
from cohezion.inference.registry import FleetRegistry, Lane, ModelEntry, Task, WeightQuant


def _entry(model_id: str) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=Lane.IGPU_ROCWMMA,
        endpoint="http://localhost:13307",
        runtime_backend="lemonade",
        task_affinity=frozenset({Task.ROUTING}),
        weight_quant=WeightQuant.INT4,
        context_window=8192,
        priority=10,
    )


def _lane_up() -> None:
    from cohezion.inference import health as health_mod
    from cohezion.inference.health import FleetHealth, LaneHealth, LaneStatus

    health_mod._LAST_RESULT = FleetHealth(
        checked_at=time.time(),
        lanes={
            "igpu_rocwmma": LaneHealth(
                "igpu_rocwmma", "http://localhost:13307", LaneStatus.UP, 10.0
            ),
        },
    )
    health_mod._LAST_CHECK_AT = time.time()


def _router_reporting(model_ids: list[str]) -> httpx.AsyncClient:
    """A client that answers /v1/models the way a healthy, UP router does."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": m} for m in model_ids]})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_route_verdict_does_not_depend_on_a_live_router(monkeypatch) -> None:
    """DISCRIMINATING: an UP router listing other models must not change a mocked route test.

    Without the conftest stub the real probe runs, sees 'fake-model' absent, and route()
    returns 'all candidates exhausted' -- exactly the flaky failure, made deterministic.
    """
    monkeypatch.setattr(fleet_mod, "_LEMONADE_LOADED_MODELS", None)
    monkeypatch.setattr(fleet_mod, "_LEMONADE_LOADED_MODELS_AT", 0.0)
    monkeypatch.setattr(
        fleet_mod, "_get_shared_client", lambda timeout: _router_reporting(["other"])
    )
    _lane_up()
    reg = FleetRegistry(models={})
    reg.models["fake-model"] = _entry("fake-model")
    dispatch = AsyncMock(return_value=("ok", 0.0, None, None))
    with (
        patch.object(fleet_mod, "_get_lemonade_health", AsyncMock(return_value=None)),
        patch.object(fleet_mod, "_dispatch_openai_compatible", dispatch),
    ):
        result = await route("hi", task=Task.ROUTING, registry=reg)
    assert result.model == "fake-model", result.attempts
    assert dispatch.await_count == 1


@pytest.mark.asyncio
async def test_residency_gate_still_skips_unloaded_candidates_when_asked() -> None:
    """The stub hides the LIVE probe, not the gate: a reported residency set is still enforced."""
    _lane_up()
    reg = FleetRegistry(models={})
    reg.models["cold"] = _entry("cold")
    dispatch = AsyncMock(return_value=("ok", 0.0, None, None))
    with (
        patch.object(fleet_mod, "_get_lemonade_loaded_models", AsyncMock(return_value={"warm"})),
        patch.object(fleet_mod, "_get_lemonade_health", AsyncMock(return_value=None)),
        patch.object(fleet_mod, "_dispatch_openai_compatible", dispatch),
    ):
        result = await route("hi", task=Task.ROUTING, registry=reg)
    assert "cold(not-loaded)" in result.attempts
    assert dispatch.await_count == 0
