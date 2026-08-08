"""Unit tests for UnifiedHybridRouter."""

import tempfile
from pathlib import Path
from cohezion.inference.delegation_logger import DelegationLogger
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


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
