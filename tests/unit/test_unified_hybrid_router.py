"""Unit tests for UnifiedHybridRouter."""

import tempfile
from pathlib import Path

# reconcile 2026-08-26: imports needed by branch-preserved code
from unittest.mock import patch

from cohezion.inference.delegation_logger import DelegationLogger
from cohezion.inference.unified_hybrid_router import HybridRouteResponse, UnifiedHybridRouter
from cohezion.reliability.oom_guard import MemoryState


def test_evi_calculation() -> None:
    router = UnifiedHybridRouter()
    # quality_gap = 0.3, task_importance = 0.8, cost Tier 1->2 = 0.25
    # EVI = (0.3 * 0.8) / 0.25 = 0.96
    evi = router.compute_evi(0.3, 0.8, 1, 2)
    assert abs(evi - 0.96) < 1e-3


def test_route_tier1_happy_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        d_logger = DelegationLogger()
        d_logger.fallback_path = Path(tmpdir) / "log.jsonl"
        router = UnifiedHybridRouter(logger_instance=d_logger)

        res = router.route(
            task_type="coding",
            task_importance=0.5,
            estimated_tier1_quality=0.85,
            target_quality_required=0.85,
        )

        assert res.selected_tier == 1
        assert res.model_name == "Qwen3-Coder-30B"
        assert res.escalated is False
        assert "Tier 1 selected" in res.reason


def test_route_tier2_escalation_when_evi_gt_075() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        d_logger = DelegationLogger()
        d_logger.fallback_path = Path(tmpdir) / "log.jsonl"
        router = UnifiedHybridRouter(logger_instance=d_logger)

        # quality_gap = 0.3, task_importance = 0.8, cost = 0.25 -> EVI = 0.96 > 0.75
        res = router.route(
            task_type="coding",
            task_importance=0.8,
            estimated_tier1_quality=0.6,
            target_quality_required=0.9,
        )

        assert res.selected_tier == 2
        assert res.model_name == "qwen3.5:397b-cloud"
        assert res.escalated is True
        assert res.evi_score > 0.75


def test_route_force_tier_override() -> None:
    router = UnifiedHybridRouter()
    res = router.route("architecture", force_tier=3)
    assert res.selected_tier == 3
    assert res.model_name == "gemini-3-pro"
    assert "force_tier=3" in res.reason


def test_route_with_flume_vae_prompt() -> None:
    router = UnifiedHybridRouter()
    res = router.route(
        task_type="coding",
        task_importance=0.5,
        prompt="Implement a deterministic matrix multiply kernel in C++",
    )
    assert res.selected_tier in (1, 2, 3)
    assert res.model_name != ""


# --- reconcile 2026-08-26: top-level symbols preserved from the branch ---
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
