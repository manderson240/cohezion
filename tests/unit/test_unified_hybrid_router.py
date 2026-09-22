"""Unit tests for UnifiedHybridRouter."""

import tempfile
import warnings
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
        assert res.model_name == "kimi-k2.7-code:cloud"
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


# Ollama Cloud retirements, 2026-09-25. The bare "deepseek-v4-flash:cloud" alias shares
# 0731's digest (verified via /api/show), so it retires too.
_RETIRED_CLOUD_MODELS = {
    "deepseek-v4-flash:0731-cloud",
    "deepseek-v4-flash:cloud",
    "qwen3.5:397b-cloud",
    "qwen3.5:cloud",  # same parameter_size + modified_at as the 397b build
    "kimi-k2.5:cloud",  # retired 2026-07-31 (/api/show says so); was still in a chain
}

# Deliberate historical records: kept (marked retired), never dispatched to.
_RETIRED_RECORD_FILES = {
    "src/cohezion/inference/registry.py",
    "src/cohezion/inference/model_card_profiles.py",
}


def _docstring_ids(tree: object) -> set[int]:
    import ast

    ids: set[int] = set()
    for node in ast.walk(tree):  # type: ignore[arg-type]
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
            if isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def test_no_source_literal_names_a_retired_cloud_model() -> None:
    """Any code string (not docstring/comment) equal to a retired id would 404 after retirement."""
    import ast

    repo = Path(__file__).resolve().parents[2]
    hits = []
    for path in sorted((repo / "src").rglob("*.py")):
        rel = path.relative_to(repo).as_posix()
        if rel in _RETIRED_RECORD_FILES:
            continue
        with warnings.catch_warnings():  # other files' bad escapes are not this test's concern
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(path.read_text(encoding="utf-8"))
        docs = _docstring_ids(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and node.value in _RETIRED_CLOUD_MODELS
                and id(node) not in docs
            ):
                hits.append(f"{rel}:{node.lineno} {node.value}")
    assert not hits, "retired cloud model ids still in code:\n" + "\n".join(hits)


def test_no_route_table_pins_a_retired_cloud_model() -> None:
    """Every module-level routing dict must resolve to a model that still exists."""
    import cohezion.inference.unified_hybrid_router as uhr

    pinned = {
        f"{name}[{key}]": value
        for name, table in vars(uhr).items()
        if isinstance(table, dict)
        for key, value in table.items()
        if isinstance(value, str)
    }
    stale = {where: model for where, model in pinned.items() if model in _RETIRED_CLOUD_MODELS}
    assert not stale, f"route tables still pin retired models: {stale}"
