import pytest
from unittest.mock import patch
from cohezion.reliability.oom_guard import MemoryState
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter, HybridRouteResponse

def test_unified_hybrid_router_local_fallback():
    router = UnifiedHybridRouter(prefer_local=True)

    with patch.object(router, "query_lemonade_local", return_value="Local NPU MoE response text"):
        with patch(
            "cohezion.inference.unified_hybrid_router.OOMGuard.get_memory_state",
            return_value=MemoryState(
                available_gb=50.0,
                total_gb=128.0,
                swap_used_gb=0.0,
                shmem_gb=0.5,
                is_safe=True,
                dynamic_floor_gb=20.0,
            ),
        ):
            res = router.route_query("Summarize Cohezion AGI architecture.")
            assert isinstance(res, HybridRouteResponse)
            assert res.verified is True
            assert res.tier_used == "Tier 1 (Local NPU MoE)"
            assert res.content == "Local NPU MoE response text"

def test_unified_hybrid_router_force_cloud():
    router = UnifiedHybridRouter(prefer_local=True)

    with patch.object(router, "query_ollama_cloud", return_value="Ollama Cloud response text"):
        res = router.route_query("Complex cloud analysis", force_cloud=True)
        assert isinstance(res, HybridRouteResponse)
        assert res.tier_used == "Tier 2 (Ollama Cloud)"
        assert res.content == "Ollama Cloud response text"
