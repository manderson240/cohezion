"""Unit tests for the CPU overflow lane (CPUInferenceEngine) in the router.

Covers the cpu_parallel activation: the lane's <=9B parameter cap, the
granite-4.2-8b-GGUF default with per-call override, the synthetic-placeholder
refusal shape, and the lane's gate-bypass contract (no ensure_resident, no
:13305 chat POST through the gated path).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.cpu_inference_engine import CPUInferenceEngine, CPUInferenceResult
from cohezion.inference.unified_hybrid_router import (
    CPU_LANE_DEFAULT_MODEL,
    CPU_LANE_MAX_PARAMS_B,
    CPU_LANE_THREADS,
    TaskClass,
    UnifiedHybridRouter,
)
from cohezion.reliability.oom_guard import MemoryState


def _cpu_result(content: str = "cpu out", backend: str = "AVX-512 Zen5 OpenMP"):
    return CPUInferenceResult(
        content=content,
        threads_used=CPU_LANE_THREADS,
        available_ram_gb=50.0,
        latency_ms=12.5,
        cpu_backend=backend,
    )


def _safe_memory() -> MemoryState:
    return MemoryState(
        available_gb=50.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        shmem_gb=0.5,
        is_safe=True,
        dynamic_floor_gb=20.0,
    )


def _health_ok():
    from cohezion.inference.lemonade_health import LemonadeHealth, RecipeProbe

    return LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="v1.0",
        status="ok",
        loaded_count=2,
        recipe_probes=[RecipeProbe(recipe="llamacpp", ok=True, latency_ms=1.0)],
        latency_ms=1.2,
    )


def test_lane_constants() -> None:
    assert CPU_LANE_THREADS == 32
    assert CPU_LANE_DEFAULT_MODEL == "granite-4.2-8b-GGUF"
    assert CPU_LANE_MAX_PARAMS_B == 9.0


def test_cpu_engine_default_model_is_granite() -> None:
    engine = CPUInferenceEngine(threads=CPU_LANE_THREADS)
    assert engine.default_model == "granite-4.2-8b-GGUF"
    assert engine.threads == 32


def test_cpu_lane_admits_models_up_to_9b() -> None:
    router = UnifiedHybridRouter(prefer_local=True)
    with patch.object(router._cpu_engine, "execute_cpu_inference", return_value=_cpu_result()) as m:
        resp = asyncio.run(router._try_cpu_overflow("prompt", "Qwen3-8B"))
    assert resp is not None
    assert resp.model_name == "Qwen3-8B"
    m.assert_called_once()


def test_cpu_lane_refuses_models_over_9b() -> None:
    router = UnifiedHybridRouter(prefer_local=True)
    with patch.object(router._cpu_engine, "execute_cpu_inference") as m:  # must never be reached
        resp = asyncio.run(router._try_cpu_overflow("prompt", "Qwen3-Coder-30B-A3B-Instruct-GGUF"))
    assert resp is None
    m.assert_not_called()


def test_cpu_lane_refuses_unparseable_size() -> None:
    router = UnifiedHybridRouter(prefer_local=True)
    with patch.object(router._cpu_engine, "execute_cpu_inference") as m:
        resp = asyncio.run(router._try_cpu_overflow("prompt", "some-model-without-size"))
    assert resp is None
    m.assert_not_called()


def test_cpu_lane_synthetic_placeholder_is_a_refusal() -> None:
    router = UnifiedHybridRouter(prefer_local=True)
    with patch.object(
        router._cpu_engine,
        "execute_cpu_inference",
        return_value=CPUInferenceResult(
            content="[CPU Zen5 Parallel Pool] Processed locally...",
            threads_used=32,
            available_ram_gb=50.0,
            latency_ms=12.5,
            cpu_backend="Fallback CPU Thread Pool",
        ),
    ):
        resp = asyncio.run(router._try_cpu_overflow("prompt", "granite-4.2-8b-GGUF"))
    assert resp is None


def test_cpu_lane_default_model_used_when_none() -> None:
    router = UnifiedHybridRouter(prefer_local=True)
    with patch.object(router._cpu_engine, "execute_cpu_inference", return_value=_cpu_result()) as m:
        resp = asyncio.run(router._try_cpu_overflow("prompt", None))
    assert resp is not None
    assert resp.model_name == "granite-4.2-8b-GGUF"
    m.assert_called_once_with("prompt", "granite-4.2-8b-GGUF")


def test_cpu_lane_tier_label_carries_thread_count() -> None:
    router = UnifiedHybridRouter(prefer_local=True)
    with patch.object(router._cpu_engine, "execute_cpu_inference", return_value=_cpu_result()):
        resp = asyncio.run(router._try_cpu_overflow("prompt", "granite-4.2-8b-GGUF"))
    assert resp is not None
    assert "32T" in resp.tier_used


@pytest.mark.asyncio
async def test_cpu_parallel_bypasses_hotswap_gate_end_to_end() -> None:
    """cpu_parallel: the lane never calls ensure_resident nor the gated chat POST."""
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=_health_ok(),
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=_safe_memory(),
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.CPUInferenceEngine.execute_cpu_inference",
            return_value=_cpu_result(),
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident",
        ) as gate_mock,
        patch(
            "cohezion.inference.unified_hybrid_router.admission_ok",
        ) as admission_mock,
        patch.object(router, "aquery_lemonade_local", new_callable=MagicMock),
    ):
        res = await router.route_by_capability(
            "parallel pool work", task_class=TaskClass.CPU_PARALLEL
        )
    assert res.tier_used.startswith("Tier 1 (CPU Overflow")
    assert res.verified is True
    gate_mock.assert_not_called()
    admission_mock.assert_not_called()
    assert router._gated_models == set()
