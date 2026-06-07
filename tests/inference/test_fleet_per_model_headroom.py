"""Behavior test: fleet.route() per-candidate headroom gate (item 132, 2026-06-07).

Refines the item-131 global OOM gate: even when the fleet-wide OOM buffer is OK, a single
candidate that individually won't fit (avail < size_gb * 1.2) is deferred. Real consumer of
resource_aware_route's headroom branch via the new ModelEntry.size_gb field.

Discriminating: with available_gb=20 (above the 16 buffer) and candidates sized 18 and 4 GB,
the 18 GB candidate (needs 21.6) must be DEFERRED and the 4 GB one dispatched. A wrong impl that
ignores size_gb dispatches the 18 GB candidate first → result.model is the 18 GB one → fails.
A candidate with size_gb=None must NOT be spuriously deferred (no fabricated size).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.competition.orchestrator.resource_guard import MemorySnapshot
from cohezion.inference.fleet import route
from cohezion.inference.registry import FleetRegistry, Lane, ModelEntry, Task, WeightQuant


def _entry(model_id: str, size_gb: float | None, priority: int) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=Lane.IGPU_ROCWMMA,
        endpoint="http://localhost:13307",
        runtime_backend="lemonade",
        task_affinity=frozenset({Task.ROUTING}),
        weight_quant=WeightQuant.INT4,
        context_window=8192,
        priority=priority,
        size_gb=size_gb,
    )


def _all_up() -> None:
    from cohezion.inference import health as health_mod
    from cohezion.inference.health import FleetHealth, LaneHealth, LaneStatus

    health_mod._LAST_RESULT = FleetHealth(
        checked_at=time.time(),
        lanes={
            "igpu_rocwmma": LaneHealth("igpu_rocwmma", "http://localhost:13307", LaneStatus.UP, 10.0),
        },
    )
    health_mod._LAST_CHECK_AT = time.time()


@pytest.mark.asyncio
async def test_oversized_candidate_deferred_smaller_dispatched() -> None:
    _all_up()
    reg = FleetRegistry(models={})
    reg.models["big"] = _entry("big", size_gb=18.0, priority=10)  # tried first, won't fit
    reg.models["small"] = _entry("small", size_gb=4.0, priority=20)  # fits
    snap = MemorySnapshot(total_gb=128.0, available_gb=20.0, used_gb=108.0)
    dispatch = AsyncMock(return_value=("ok", 0.0, None, None))

    with patch("cohezion.inference.fleet._dispatch_openai_compatible", dispatch):
        result = await route("hi", task=Task.ROUTING, registry=reg, resource_snapshot=snap)

    assert result.model == "small", f"oversized 'big' should be deferred, got {result.attempts}"
    assert any("headroom" in a.lower() for a in result.attempts if "big" in a)


@pytest.mark.asyncio
async def test_unknown_size_not_spuriously_deferred() -> None:
    _all_up()
    reg = FleetRegistry(models={})
    reg.models["nosize"] = _entry("nosize", size_gb=None, priority=10)
    snap = MemorySnapshot(total_gb=128.0, available_gb=20.0, used_gb=108.0)
    dispatch = AsyncMock(return_value=("ok", 0.0, None, None))

    with patch("cohezion.inference.fleet._dispatch_openai_compatible", dispatch):
        result = await route("hi", task=Task.ROUTING, registry=reg, resource_snapshot=snap)

    assert result.model == "nosize"  # no fabricated size → dispatched normally
    assert dispatch.await_count == 1
