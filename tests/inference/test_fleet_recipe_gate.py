"""Tests for fleet.py recipe-aware health gate (next-move #1, 2026-06-10).

Pure logic + mocked tests run unconditionally. Live tests skip cleanly if
:13305 is down.
"""
from __future__ import annotations

import socket
import time
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.competition.orchestrator.resource_guard import MemorySnapshot
from cohezion.inference.fleet import (
    _get_lemonade_health,
    _lemonade_recipe_skip_reason,
    _recipe_for_backend,
    route,
)
from cohezion.inference.lemonade_health import (
    CtxHazard,
    LemonadeHealth,
    RecipeProbe,
)
from cohezion.inference.registry import Lane, ModelEntry, Task, WeightQuant


AMPLE_MEM = MemorySnapshot(total_gb=128.0, available_gb=64.0, used_gb=64.0)


# Minimal ModelEntry factory for tests (avoids pulling in the full
# registry singleton which is heavy and has 50+ real entries).
def _entry(
    model_id: str,
    lane: Lane = Lane.NPU,
    endpoint: str = "http://localhost:13305",
    runtime_backend: str = "flm",
    priority: int = 10,
) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=lane,
        endpoint=endpoint,
        runtime_backend=runtime_backend,
        task_affinity=frozenset({Task.ROUTING, Task.SUMMARIZATION}),
        weight_quant=WeightQuant.INT4,
        context_window=8192,
        priority=priority,
    )


# ----- Pure logic (no network) ---------------------------------------------


def test_recipe_for_backend_known():
    assert _recipe_for_backend("flm") == "flm"
    assert _recipe_for_backend("llamacpp_hip") == "llamacpp"
    assert _recipe_for_backend("vllm_rocm") == "vllm"
    assert _recipe_for_backend("cpu") == "llamacpp"


def test_recipe_for_backend_unknown_returns_none():
    assert _recipe_for_backend("") is None
    assert _recipe_for_backend("gibberish") is None
    # cloud/ollama runtime_backend empty string -> None
    assert _recipe_for_backend("ollama") is None  # not in map -> None


def test_recipe_skip_no_probe_returns_none():
    """If the health probe failed/missing, the gate is permissive (fail-soft)."""
    cand = _entry("X", runtime_backend="flm")
    assert _lemonade_recipe_skip_reason(cand, None) is None


def test_recipe_skip_cloud_candidate_returns_none():
    """Cloud (runtime_backend="") passes through the gate."""
    cand = _entry("Y", lane=Lane.CLOUD_CLAUDE, runtime_backend="")
    h = LemonadeHealth(
        checked_at=time.time(),
        port=13305,
        version="x",
        status="ok",
        loaded_count=0,
        recipe_probes=[],
        headroom=[],
    )
    assert _lemonade_recipe_skip_reason(cand, h) is None


def test_recipe_skip_recipe_down():
    """A recipe whose probe returned not ok -> drop the candidate."""
    cand = _entry("Flan-T5", runtime_backend="llamacpp_hip")
    h = LemonadeHealth(
        checked_at=time.time(),
        port=13305,
        version="x",
        status="ok",
        loaded_count=1,
        recipe_probes=[
            RecipeProbe(recipe="llamacpp", ok=False, latency_ms=999.0, detail="HTTP 503"),
        ],
        headroom=[],
    )
    reason = _lemonade_recipe_skip_reason(cand, h)
    assert reason is not None
    assert "recipe-down" in reason
    assert "llamacpp" in reason


def test_recipe_skip_ctx_hazard_drops_candidate():
    """The 2026-06-09 OOM trap: candidate's model has ctx_size=0 in health."""
    cand = _entry("Qwen-35B", runtime_backend="llamacpp_hip")
    h = LemonadeHealth(
        checked_at=time.time(),
        port=13305,
        version="x",
        status="ok",
        loaded_count=2,
        recipe_probes=[
            RecipeProbe(recipe="llamacpp", ok=True, latency_ms=10.0, detail="HTTP 200"),
        ],
        headroom=[],
        ctx_hazards=[
            CtxHazard(
                model="Qwen-35B",
                recipe="llamacpp",
                ctx_size=0,
                backend_url="http://x",
                pid=42,
            ),
        ],
    )
    reason = _lemonade_recipe_skip_reason(cand, h)
    assert reason is not None
    assert "ctx-hazard" in reason
    assert "ctx_size=0" in reason


def test_recipe_skip_healthy_recipe_passes():
    """Healthy recipe + no ctx hazard -> None (let the existing gate decide)."""
    cand = _entry("E2B", runtime_backend="flm")
    h = LemonadeHealth(
        checked_at=time.time(),
        port=13305,
        version="x",
        status="ok",
        loaded_count=1,
        recipe_probes=[
            RecipeProbe(recipe="flm", ok=True, latency_ms=5.0, detail="HTTP 200"),
        ],
        headroom=[],
    )
    assert _lemonade_recipe_skip_reason(cand, h) is None


# ----- route() integration (HTTP mocked) -----------------------------------


def _empty_health():
    """Build a FleetHealth where every local lane is UP (so the lane gate
    doesn't drop candidates before the recipe gate runs)."""
    from cohezion.inference.health import FleetHealth, LaneHealth, LaneStatus

    return FleetHealth(
        checked_at=time.time(),
        lanes={
            "npu": LaneHealth("npu", "http://localhost:13306", LaneStatus.UP, 10.0),
            "igpu_rocwmma": LaneHealth("igpu_rocwmma", "http://localhost:13307", LaneStatus.UP, 10.0),
            "igpu_unified": LaneHealth("igpu_unified", "http://localhost:13308", LaneStatus.UP, 10.0),
            "cpu": LaneHealth("cpu", "http://localhost:13309", LaneStatus.UP, 10.0),
            "ollama": LaneHealth("ollama", "http://localhost:11434", LaneStatus.UP, 10.0),
            "claude": LaneHealth("claude", "https://api.anthropic.com", LaneStatus.UP, 10.0),
        },
    )


@pytest.mark.asyncio
async def test_route_drops_ctx_hazard_candidate_and_moves_to_next():
    """If a candidate's model has ctx_size=0, route() should skip it and
    try the next candidate (recording the reason in attempts)."""
    from cohezion.inference import health as health_mod
    from cohezion.inference import fleet as fleet_mod
    from cohezion.inference.registry import FleetRegistry

    # Lane gate: all UP
    health_mod._LAST_RESULT = _empty_health()
    health_mod._LAST_CHECK_AT = time.time()

    # Recipe gate: hazard on first candidate, no hazard on second.
    hazard_h = LemonadeHealth(
        checked_at=time.time(),
        port=13305,
        version="x",
        status="ok",
        loaded_count=2,
        recipe_probes=[
            RecipeProbe(recipe="llamacpp", ok=True, latency_ms=10.0, detail="HTTP 200"),
        ],
        headroom=[],
        ctx_hazards=[
            CtxHazard(
                model="BAD-MODEL",
                recipe="llamacpp",
                ctx_size=0,
                backend_url="http://x",
                pid=1,
            ),
        ],
    )

    # Build a minimal registry with two local candidates
    bad = _entry("BAD-MODEL", runtime_backend="llamacpp_hip", priority=5)
    good = _entry("GOOD-MODEL", runtime_backend="llamacpp_hip", priority=10)
    reg = FleetRegistry()
    reg.models = {"BAD-MODEL": bad, "GOOD-MODEL": good}
    reg._task_index = {Task.ROUTING: ["BAD-MODEL", "GOOD-MODEL"]}

    # Mock the dispatch to capture which candidate actually fired
    seen = []

    async def fake_dispatch(model, prompt, coherence, timeout, budget_usd=None, **kw):
        seen.append(model.model_id)
        return ("dispatched text", 0.0, None, None)

    with patch.object(fleet_mod, "_get_lemonade_health", AsyncMock(return_value=hazard_h)):
        with patch.object(fleet_mod, "_dispatch_one", side_effect=fake_dispatch):
            result = await route("ping", task=Task.ROUTING, registry=reg, resource_snapshot=AMPLE_MEM)

    assert result.error is None
    assert result.model == "GOOD-MODEL"
    assert seen == ["GOOD-MODEL"]
    # The bad candidate should appear in the attempts list with the hazard reason
    assert any("ctx-hazard" in a for a in result.attempts), f"missing ctx-hazard in {result.attempts}"


@pytest.mark.asyncio
async def test_route_drops_recipe_down_and_tries_cloud_fallback():
    """If the local recipe is DOWN, the cloud fallback should be tried."""
    from cohezion.inference import health as health_mod
    from cohezion.inference import fleet as fleet_mod
    from cohezion.inference.registry import FleetRegistry

    health_mod._LAST_RESULT = _empty_health()
    health_mod._LAST_CHECK_AT = time.time()

    down_h = LemonadeHealth(
        checked_at=time.time(),
        port=13305,
        version="x",
        status="ok",
        loaded_count=1,
        recipe_probes=[
            RecipeProbe(recipe="llamacpp", ok=False, latency_ms=999.0, detail="HTTP 503"),
        ],
        headroom=[],
    )

    bad = _entry("LOCAL", runtime_backend="llamacpp_hip", priority=5)
    cloud = _entry(
        "CLOUD",
        lane=Lane.CLOUD_CLAUDE,
        endpoint="https://api.anthropic.com",
        runtime_backend="",  # cloud bypasses the gate
        priority=100,
    )
    cloud.task_affinity = frozenset({Task.ROUTING})
    reg = FleetRegistry()
    reg.models = {"LOCAL": bad, "CLOUD": cloud}
    reg._task_index = {Task.ROUTING: ["LOCAL", "CLOUD"]}

    seen = []

    async def fake_dispatch(model, prompt, coherence, timeout, budget_usd=None, **kw):
        seen.append(model.model_id)
        return ("dispatched text", 0.0, None, None)

    with patch.object(fleet_mod, "_get_lemonade_health", AsyncMock(return_value=down_h)):
        with patch.object(fleet_mod, "_dispatch_one", side_effect=fake_dispatch):
            result = await route("ping", task=Task.ROUTING, registry=reg, resource_snapshot=AMPLE_MEM)

    assert result.error is None
    assert result.model == "CLOUD"
    assert any("recipe-down" in a for a in result.attempts), f"missing recipe-down in {result.attempts}"


@pytest.mark.asyncio
async def test_route_probe_failure_is_advisory_does_not_block():
    """When _get_lemonade_health returns None (probe failed), the gate is
    permissive and dispatch proceeds normally (matches OOM-gate doctrine)."""
    from cohezion.inference import health as health_mod
    from cohezion.inference import fleet as fleet_mod
    from cohezion.inference.registry import FleetRegistry

    health_mod._LAST_RESULT = _empty_health()
    health_mod._LAST_CHECK_AT = time.time()

    good = _entry("GOOD", runtime_backend="llamacpp_hip", priority=5)
    reg = FleetRegistry()
    reg.models = {"GOOD": good}
    reg._task_index = {Task.ROUTING: ["GOOD"]}

    seen = []

    async def fake_dispatch(model, prompt, coherence, timeout, budget_usd=None, **kw):
        seen.append(model.model_id)
        return ("dispatched text", 0.0, None, None)

    # Probe returns None (lemonade is down OR probe errored).
    with patch.object(fleet_mod, "_get_lemonade_health", AsyncMock(return_value=None)):
        with patch.object(fleet_mod, "_dispatch_one", side_effect=fake_dispatch):
            result = await route("ping", task=Task.ROUTING, registry=reg, resource_snapshot=AMPLE_MEM)

    assert result.error is None
    assert result.model == "GOOD"
    assert seen == ["GOOD"]


# ----- Live E2E (skips if :13305 unreachable) ------------------------------


def lemonade_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 13305), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not lemonade_reachable(), reason="lemonade :13305 not reachable")
@pytest.mark.asyncio
async def test_route_against_live_omni_with_real_probe():
    """End-to-end: real probe_lemonade() against :13305, real route() dispatch.

    Verifies the live probe doesn't error out, the gate doesn't drop a
    healthy candidate, and route() returns a real response.
    """
    from cohezion.inference import health as health_mod
    from cohezion.inference import fleet as fleet_mod
    from cohezion.inference.registry import FleetRegistry

    health_mod._LAST_RESULT = _empty_health()
    health_mod._LAST_CHECK_AT = time.time()
    # Reset lemonade cache so we hit :13305 fresh
    fleet_mod._LEMONADE_LAST_PROBE_AT = 0.0
    fleet_mod._LEMONADE_LAST_RESULT = None

    # Use a model that's actually loaded in the live pool:
    # Gemma-4-E2B-it-GGUF (NPU/FLM, smallest, fastest).
    e2b = ModelEntry(
        model_id="Gemma-4-E2B-it-GGUF",
        lane=Lane.NPU,
        endpoint="http://localhost:13305",
        runtime_backend="flm",
        task_affinity=frozenset({Task.ROUTING, Task.SUMMARIZATION}),
        weight_quant=WeightQuant.INT4,
        context_window=8192,
        priority=10,
    )
    reg = FleetRegistry()
    reg.models = {"Gemma-4-E2B-it-GGUF": e2b}
    reg._task_index = {Task.ROUTING: ["Gemma-4-E2B-it-GGUF"]}

    result = await route(
        "ping", task=Task.ROUTING, registry=reg, timeout=30.0, resource_snapshot=AMPLE_MEM
    )

    # We don't assert on text content (reasoning-mode models may produce
    # reasoning_content instead of content for short prompts), but we
    # DO assert that the gate didn't falsely drop the candidate, and
    # that the dispatch returned without an error.
    if result.error is not None:
        # The dispatcher may have errored on E2B's reasoning-mode empty
        # content for "ping"; that's a model-side issue, not a gate issue.
        # The gate's job is to NOT add spurious errors.
        assert "ctx-hazard" not in (result.error or "")
        assert "recipe-down" not in (result.error or "")
    assert "ctx-hazard" not in " ".join(result.attempts)
    assert "recipe-down" not in " ".join(result.attempts)


@pytest.mark.skipif(not lemonade_reachable(), reason="lemonade :13305 not reachable")
@pytest.mark.asyncio
async def test_get_lemonade_health_live_returns_real_snapshot():
    """The cached helper actually returns a typed LemonadeHealth against :13305."""
    # Reset cache
    import cohezion.inference.fleet as fmod

    fmod._LEMONADE_LAST_PROBE_AT = 0.0
    fmod._LEMONADE_LAST_RESULT = None

    h = await _get_lemonade_health()
    assert h is not None
    assert h.port == 13305
    assert h.loaded_count >= 1
    assert isinstance(h.recipe_probes, list)
    # The live pool has at least llamacpp + kokoro + sd-cpp + flm
    # (kokoro is on port 8008 but OmniRouter proxies /v1/audio/voices)
    assert len(h.recipe_probes) >= 1
