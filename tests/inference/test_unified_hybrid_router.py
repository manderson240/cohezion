import time
from unittest.mock import AsyncMock, patch

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


@pytest.mark.asyncio
async def test_route_by_capability_tier1_reasoning(mock_safe_memory, mock_lemonade_health):
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
async def test_route_by_capability_coding_igpu(mock_safe_memory, mock_lemonade_health):
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
async def test_route_by_capability_embeddings(mock_safe_memory, mock_lemonade_health):
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


_ROUTE_CASES = [
    (tt, p, imp)
    for imp in (0.1, 0.3, 0.5, 0.9)
    for tt, p in [
        ("coding", "Write a python function to parse CSV"),
        ("fast_qa", "hi"),
        ("reasoning", "Prove that sqrt 2 is irrational"),
    ]
]


def test_prompt_text_never_changes_the_route():
    """quality_gap is declared-quality only. A cosine(prompt, boilerplate) term makes every
    prompt look 'far' from the boilerplate under a real encoder and escalates everything
    (measured 3/12 -> 9/12 Tier 2 with MiniLM, including 'hi')."""
    router = UnifiedHybridRouter()
    router.logger.log_delegation = lambda e: None
    for task_type, prompt, importance in _ROUTE_CASES:
        with_prompt = router.route(task_type, task_importance=importance, prompt=prompt)
        without = router.route(task_type, task_importance=importance)
        assert with_prompt.selected_tier == without.selected_tier, (task_type, prompt, importance)
        assert with_prompt.evi_score == without.evi_score


def test_trivial_prompt_stays_on_tier1_at_high_importance():
    router = UnifiedHybridRouter()
    router.logger.log_delegation = lambda e: None
    assert router.route("fast_qa", task_importance=0.5, prompt="hi").selected_tier == 1
