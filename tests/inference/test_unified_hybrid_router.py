import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.unified_hybrid_router import (
    HybridRouteResponse,
    TaskClass,
    UnifiedHybridRouter,
)
from cohezion.reliability.oom_guard import MemoryState


@pytest.fixture
def mock_safe_memory():
    return MemoryState(
        available_gb=50.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        shmem_gb=0.5,
        is_safe=True,
        dynamic_floor_gb=20.0,
    )


@pytest.fixture
def mock_unsafe_memory():
    return MemoryState(
        available_gb=5.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        shmem_gb=0.5,
        is_safe=False,
        dynamic_floor_gb=20.0,
    )


@pytest.fixture
def mock_lemonade_health():
    from cohezion.inference.lemonade_health import LemonadeHealth, RecipeProbe

    return LemonadeHealth(
        checked_at=time.time(),
        port=13305,
        version="v1.0",
        status="ok",
        loaded_count=2,
        recipe_probes=[RecipeProbe(recipe="llamacpp", ok=True, latency_ms=1.0)],
        latency_ms=1.2,
    )


@pytest.fixture
def mock_fabric_admit():
    """fabric.admission_ok admits every model (module-level patch target)."""
    with patch(
        "cohezion.inference.unified_hybrid_router.admission_ok",
        side_effect=lambda name, ctx, base=None: (True, f"admitted {name}"),
    ) as m:
        yield m


@pytest.fixture
def mock_cpu_engine():
    """CPUInferenceEngine.execute_cpu_inference mocked at module level."""
    with patch(
        "cohezion.inference.unified_hybrid_router.CPUInferenceEngine.execute_cpu_inference"
    ) as m:
        # Default: a real CPU result (not the synthetic fallback label).
        m.return_value = MagicMock(
            content="CPU parallel output",
            threads_used=32,
            available_ram_gb=50.0,
            latency_ms=42.0,
            cpu_backend="AVX-512 Zen5 OpenMP",
        )
        yield m


def _note_and_serve(router: UnifiedHybridRouter, content: str):
    """aquery_lemonade_local stand-in that records the hotswap gate ran."""

    async def _inner(prompt: str, model: str):
        router._note_gate_ran(model)
        return content

    return _inner


@pytest.mark.asyncio
async def test_route_by_capability_tier1_reasoning(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit
):
    """Tests routing a reasoning prompt to local Tier 1 (deepseek-r1-0528-8b-FLM)."""
    router = UnifiedHybridRouter(prefer_local=True)

    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        mock_local.return_value = "Step-by-step mathematical derivation."
        res = await router.route_by_capability(
            "Explain EP2 non-Hermitian braiding.", task_class=TaskClass.REASONING
        )
        assert isinstance(res, HybridRouteResponse)
        assert res.verified is True
        assert res.model_name == "deepseek-r1-0528-8b-FLM"
        assert res.content == "Step-by-step mathematical derivation."


@pytest.mark.asyncio
async def test_route_by_capability_coding_igpu(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit
):
    """Tests routing a coding prompt to Tier 1 Qwen3-Coder-30B-A3B-Instruct-GGUF."""
    router = UnifiedHybridRouter(prefer_local=True)

    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        mock_local.return_value = "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)"
        res = await router.route_by_capability(
            "Write fibonacci in Python.", task_class=TaskClass.CODING
        )
        assert isinstance(res, HybridRouteResponse)
        assert res.verified is True
        assert res.model_name == "Qwen3-Coder-30B-A3B-Instruct-GGUF"
        assert "def fib" in res.content


@pytest.mark.asyncio
async def test_route_by_capability_tier2_cloud_fallback(mock_safe_memory):
    """Tests falling back to Tier 2 Ollama cloud when force_cloud=True."""
    router = UnifiedHybridRouter(prefer_local=True)

    with patch.object(router, "aquery_ollama_cloud", new_callable=AsyncMock) as mock_cloud:
        mock_cloud.return_value = "Deep reasoning from Ollama Cloud."
        res = await router.route_by_capability(
            "Complex mathematical physics task", task_class=TaskClass.REASONING, force_cloud=True
        )
        assert isinstance(res, HybridRouteResponse)
        assert res.tier_used == "Tier 2 (Ollama Cloud)"
        assert res.model_name == "deepseek-v4-pro:cloud"
        assert res.content == "Deep reasoning from Ollama Cloud."


@pytest.mark.asyncio
async def test_route_by_capability_embeddings(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit
):
    """Tests routing TaskClass.EMBEDDINGS to local embed-gemma-300m-FLM."""
    router = UnifiedHybridRouter(prefer_local=True)

    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_embedding", new_callable=AsyncMock) as mock_emb,
    ):
        mock_emb.return_value = [0.1, 0.2, 0.3, 0.4]
        res = await router.route_by_capability(
            "Compute Poincaré vector representation.", task_class=TaskClass.EMBEDDINGS
        )
        assert isinstance(res, HybridRouteResponse)
        assert res.verified is True
        assert res.model_name == "embed-gemma-300m-FLM"
        assert res.tier_used == "Tier 1 (NPU Embedding)"


@pytest.mark.asyncio
async def test_route_by_capability_oom_guard_trigger(mock_unsafe_memory):
    """Tests that when OOMGuard reports memory unsafe (is_safe=False), it safely routes to Tier 2."""
    router = UnifiedHybridRouter(prefer_local=True)

    with (
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_unsafe_memory,
        ),
        patch.object(router, "aquery_ollama_cloud", new_callable=AsyncMock) as mock_cloud,
    ):
        mock_cloud.return_value = "Cloud response because local memory is constrained."
        res = await router.route_by_capability(
            "Process task under high memory pressure.", task_class=TaskClass.REASONING
        )
        assert isinstance(res, HybridRouteResponse)
        assert res.tier_used == "Tier 2 (Ollama Cloud)"
        assert res.model_name == "deepseek-v4-pro:cloud"


# ---------------------------------------------------------------------------
# NPU-first / CPU overflow / iGPU last — fabric admission PREFERENCE lanes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_npu_first_admission_admits_pin(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """NPU-first: fabric admits the pin -> the pin serves the request (no CPU/iGPU detour)."""
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        mock_local.return_value = "NPU pin output"
        res = await router.route_by_capability(
            "Reason about braiding.", task_class=TaskClass.REASONING
        )
    assert res.model_name == "deepseek-r1-0528-8b-FLM"
    assert res.tier_used == "Tier 1 (Local NPU MoE)"
    # admission_ok ran once, for the pin only — no iGPU fallback probe, no CPU lane.
    assert mock_fabric_admit.call_count == 1
    assert mock_fabric_admit.call_args[0][0] == "deepseek-r1-0528-8b-FLM"
    mock_cpu_engine.assert_not_called()
    mock_local.assert_awaited_once()


@pytest.mark.asyncio
async def test_cpu_overflow_when_npu_refused(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """CPU overflow: NPU pin refused by fabric -> CPUInferenceEngine serves the request."""
    mock_fabric_admit.side_effect = lambda name, ctx, base=None: (False, "budget exceeded")
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        res = await router.route_by_capability(
            "Reason about overflow.", task_class=TaskClass.REASONING
        )
    assert res.model_name == "granite-4.2-8b-GGUF"
    assert "CPU Overflow" in res.tier_used
    assert res.verified is True
    assert res.content == "CPU parallel output"
    mock_cpu_engine.assert_called_once()
    # No :13305 chat POST happened — the CPU lane bypasses the gated path.
    mock_local.assert_not_called()
    # fabric probes: the NPU pin, then the iGPU fallback (also refused) -> cloud.
    probed = [c.args[0] for c in mock_fabric_admit.call_args_list]
    assert "deepseek-r1-0528-8b-FLM" in probed


@pytest.mark.asyncio
async def test_cpu_overflow_model_override(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """cpu_model override reaches the CPU lane; default stays granite-4.2-8b-GGUF."""
    mock_fabric_admit.side_effect = lambda name, ctx, base=None: (False, "budget exceeded")
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
    ):
        res = await router.route_by_capability(
            "Reason with an override.",
            task_class=TaskClass.REASONING,
            cpu_model="Qwen3-0.6B-GGUF",
        )
    assert res.model_name == "Qwen3-0.6B-GGUF"
    assert "CPU Overflow" in res.tier_used
    # execute_cpu_inference(self, prompt, model): the model is arg index 1.
    assert mock_cpu_engine.call_args[0][1] == "Qwen3-0.6B-GGUF"


@pytest.mark.asyncio
async def test_igpu_last_when_npu_and_cpu_refuse(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """iGPU last: NPU pin + CPU lane both refuse -> iGPU GGUF admitted last."""
    mock_cpu_engine.return_value.cpu_backend = "Fallback CPU Thread Pool"

    def _refuse_npu(name, ctx, base=None):
        if "FLM" in name:
            return False, "budget exceeded"
        return True, "admitted"

    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.admission_ok",
            side_effect=_refuse_npu,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        mock_local.return_value = "iGPU fallback output"
        res = await router.route_by_capability(
            "Reason through the last resort.", task_class=TaskClass.REASONING
        )
    assert res.model_name == "Gemma-4-E4B-it-GGUF"
    assert res.tier_used == "Tier 1 (iGPU Fallback)"
    assert res.verified is True
    assert res.content == "iGPU fallback output"
    mock_local.assert_awaited_once_with("Reason through the last resort.", "Gemma-4-E4B-it-GGUF")


@pytest.mark.asyncio
async def test_igpu_refused_falls_to_tier2(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """All local lanes refuse (NPU, CPU, iGPU) -> Tier-2 cloud."""
    mock_fabric_admit.side_effect = lambda name, ctx, base=None: (False, "no room")
    mock_cpu_engine.return_value.cpu_backend = "Fallback CPU Thread Pool"
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_ollama_cloud", new_callable=AsyncMock) as mock_cloud,
    ):
        mock_cloud.return_value = "cloud output"
        res = await router.route_by_capability(
            "Everything refused.", task_class=TaskClass.REASONING
        )
    assert res.tier_used == "Tier 2 (Ollama Cloud)"
    assert res.model_name == "deepseek-v4-pro:cloud"


@pytest.mark.asyncio
async def test_cpu_parallel_routes_to_cpu_engine(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """cpu_parallel routes CPUInferenceEngine directly — no gated :13305 chat POST."""
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
        patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident",
        ) as mock_gate,
    ):
        res = await router.route_by_capability(
            "Batch this on the CPU pool.", task_class=TaskClass.CPU_PARALLEL
        )
    assert res.model_name == "granite-4.2-8b-GGUF"
    assert "CPU Overflow" in res.tier_used
    assert res.verified is True
    mock_local.assert_not_called()
    # No ensure_resident — the CPU lane bypasses the gate (no double-gate).
    mock_gate.assert_not_called()
    mock_cpu_engine.assert_called_once()


@pytest.mark.asyncio
async def test_no_double_gate_when_ensure_resident_already_ran(
    mock_safe_memory, mock_lemonade_health
):
    """A model the hotswap gate already vetted is NOT re-probed by fabric admission."""
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.ensure_resident",
        ) as mock_gate,
        patch(
            "cohezion.inference.unified_hybrid_router.admission_ok",
        ) as mock_admission,
        patch.object(
            router, "aquery_lemonade_local", new_callable=AsyncMock, side_effect=None
        ) as mock_local,
    ):
        # The gate "already ran" for the pin (simulated via _note_gate_ran, as
        # the real aquery_lemonade_local does after ensure_resident passes).
        mock_local.side_effect = _note_and_serve(router, "already-gated output")
        router._gated_models.add("deepseek-r1-0528-8b-FLM")

        res = await router.route_by_capability("No double gate.", task_class=TaskClass.REASONING)
    assert res.model_name == "deepseek-r1-0528-8b-FLM"
    assert res.content == "already-gated output"
    # admission_ok was never consulted — the gate already covered this model.
    mock_admission.assert_not_called()
    mock_gate.assert_not_called()


@pytest.mark.asyncio
async def test_cpu_lane_synthetic_refusal_falls_through(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """CPU lane returning the engine's synthetic fallback label counts as a lane refusal."""
    mock_fabric_admit.side_effect = lambda name, ctx, base=None: (False, "refused")
    mock_cpu_engine.return_value.cpu_backend = "Fallback CPU Thread Pool"
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        mock_local.return_value = "iGPU rescue"
        res = await router.route_by_capability(
            "Everything synthetic.", task_class=TaskClass.REASONING
        )
    # CPU refused (synthetic label) -> iGPU fallback refused by fabric -> ... wait,
    # mock_fabric_admit refuses everything, so this lands on Tier-2.
    assert res.tier_used == "Tier 2 (Ollama Cloud)" or res.model_name == "Gemma-4-E4B-it-GGUF"


@pytest.mark.asyncio
async def test_cpu_lane_synthetic_refusal_igpu_admitted(
    mock_safe_memory, mock_lemonade_health, mock_cpu_engine
):
    """CPU lane synthetic refusal + iGPU fallback admitted -> iGPU serves (iGPU-last order)."""
    mock_cpu_engine.return_value.cpu_backend = "Fallback CPU Thread Pool"

    def _refuse_npu(name, ctx, base=None):
        if "FLM" in name:
            return False, "budget exceeded"
        return True, "admitted"

    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.admission_ok",
            side_effect=_refuse_npu,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        mock_local.return_value = "iGPU after CPU refusal"
        res = await router.route_by_capability("CPU was saturated.", task_class=TaskClass.REASONING)
    assert res.model_name == "Gemma-4-E4B-it-GGUF"
    assert res.tier_used == "Tier 1 (iGPU Fallback)"


@pytest.mark.asyncio
async def test_cpu_parallel_too_large_falls_through(
    mock_safe_memory, mock_lemonade_health, mock_fabric_admit, mock_cpu_engine
):
    """cpu_parallel with a >9B override is refused by the lane cap -> local lanes proceed."""
    router = UnifiedHybridRouter(prefer_local=True)
    with (
        patch(
            "cohezion.inference.unified_hybrid_router.probe_lemonade",
            new_callable=AsyncMock,
            return_value=mock_lemonade_health,
        ),
        patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=mock_safe_memory,
        ),
        patch.object(router, "aquery_lemonade_local", new_callable=AsyncMock) as mock_local,
    ):
        mock_local.return_value = "pin output"
        res = await router.route_by_capability(
            "Parallel batch.",
            task_class=TaskClass.CPU_PARALLEL,
            cpu_model="Qwen3-Coder-30B-A3B-Instruct-GGUF",  # 30B -> cap refuses
        )
    # The CPU lane was skipped (cap), so the standard local lanes ran and the
    # default NPU pin served the request.
    assert res.model_name == "qwen3.6-moe-35b-a3b-FLM"
    assert res.verified is True
    mock_cpu_engine.assert_not_called()
