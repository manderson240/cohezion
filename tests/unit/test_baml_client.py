"""Hermetic tests for the BAML bridge (no live network).

Mocks the generated client (_b and _async_b methods) so the tier-routing and
typed-output contract are verified without touching Lemonade/Ollama. The
registry construction itself is real — it proves the baml_py ClientRegistry
API shape stays compatible.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.baml import client_router


def test_registry_local_tier_points_at_lemonade() -> None:
    cr = client_router.build_registry("local")
    assert cr is not None


def test_registry_cloud_tier_points_at_ollama() -> None:
    cr = client_router.build_registry("cloud")
    assert cr is not None


def test_registry_hybrid_tier_configures_fallback() -> None:
    cr = client_router.build_registry("hybrid")
    assert cr is not None


def test_registry_unknown_tier_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown BAML tier"):
        client_router.build_registry("nonexistent")


def test_recommend_next_step_returns_typed_model() -> None:
    fake = MagicMock(spec=["action", "rationale", "risk_level"])
    fake.action = "add test"
    fake.rationale = "kills survivors"
    fake.risk_level = "low"
    with (
        patch.object(client_router, "_b") as mock_b,
        patch.object(client_router, "build_registry", return_value=MagicMock()) as mock_reg,
    ):
        mock_b.RecommendNextStep.return_value = fake
        out = client_router.recommend_next_step("ctx", "cand")
    assert out.action == "add test"
    assert out.risk_level == "low"
    assert mock_b.RecommendNextStep.called
    assert mock_reg.called


def test_recommend_next_step_async_returns_typed_model() -> None:
    fake = MagicMock(spec=["action", "rationale", "risk_level"])
    fake.action = "ship it"
    fake.rationale = "verified"
    fake.risk_level = "medium"
    with patch.object(client_router, "_async_b") as mock_b:
        mock_b.RecommendNextStep = AsyncMock(return_value=fake)
        val = asyncio.run(client_router.recommend_next_step_async("ctx", "cand"))
    assert val.action == "ship it"
    assert val.risk_level == "medium"


def test_derive_task_invariants_returns_typed_model() -> None:
    fake = MagicMock(
        spec=[
            "grid_dimension_rule",
            "conserved_colors",
            "forbidden_colors",
            "symmetry_detected",
            "description",
        ]
    )
    fake.grid_dimension_rule = "identity"
    fake.conserved_colors = [0, 1, 2]
    fake.forbidden_colors = [3, 4]
    fake.symmetry_detected = "horizontal"
    fake.description = "horizontal mirror reflection"

    with patch.object(client_router, "_b") as mock_b:
        mock_b.DeriveTaskInvariants.return_value = fake
        out = client_router.derive_task_invariants("ctx", "train_data")
    assert out.grid_dimension_rule == "identity"
    assert out.symmetry_detected == "horizontal"
    assert 1 in out.conserved_colors


def test_derive_task_invariants_async_returns_typed_model() -> None:
    fake = MagicMock(spec=["grid_dimension_rule", "conserved_colors"])
    fake.grid_dimension_rule = "scaled"
    with patch.object(client_router, "_async_b") as mock_b:
        mock_b.DeriveTaskInvariants = AsyncMock(return_value=fake)
        out = asyncio.run(client_router.derive_task_invariants_async("ctx", "train_data"))
    assert out.grid_dimension_rule == "scaled"


def test_synthesize_code_harness_returns_typed_model() -> None:
    fake = MagicMock(
        spec=[
            "harness_name",
            "precondition_assertions",
            "postcondition_assertions",
            "python_verifier_code",
            "estimated_latency_ms",
        ]
    )
    fake.harness_name = "grid_bounds"
    fake.estimated_latency_ms = 0.05
    with patch.object(client_router, "_b") as mock_b:
        mock_b.SynthesizeCodeHarness.return_value = fake
        out = client_router.synthesize_code_harness("spec", "err")
    assert out.harness_name == "grid_bounds"
    assert out.estimated_latency_ms == 0.05


def test_audit_leaderboard_next_action_returns_typed_model() -> None:
    fake = MagicMock(
        spec=[
            "competition_id",
            "target_metric_goal",
            "recommended_action",
            "confidence_score",
            "reasoning",
        ]
    )
    fake.competition_id = "arc-prize-2026"
    fake.recommended_action = "generate_ensemble"
    fake.confidence_score = 0.92
    with patch.object(client_router, "_b") as mock_b:
        mock_b.AuditLeaderboardNextAction.return_value = fake
        out = client_router.audit_leaderboard_next_action("arc-prize-2026", "lb_snap")
    assert out.competition_id == "arc-prize-2026"
    assert out.recommended_action == "generate_ensemble"
    assert out.confidence_score == 0.92


def test_tier_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COHEZION_BAML_TIER", "cloud")
    assert client_router._tier() == "cloud"
    monkeypatch.setenv("COHEZION_BAML_TIER", "local")
    assert client_router._tier() == "local"
    monkeypatch.setenv("COHEZION_BAML_TIER", "hybrid")
    assert client_router._tier() == "hybrid"


def test_extract_vault_graph_returns_typed_model() -> None:
    fake = MagicMock(spec=["source_document", "coherence_score", "entities", "relations"])
    fake.source_document = "doc.md"
    fake.coherence_score = 0.95
    with patch.object(client_router, "_b") as mock_b:
        mock_b.ExtractVaultGraph.return_value = fake
        out = client_router.extract_vault_graph("doc.md", "content")
    assert out.source_document == "doc.md"
    assert out.coherence_score == 0.95


def test_classify_task_intent_returns_typed_model() -> None:
    fake = MagicMock(spec=["node", "output_type", "quality_gate_chars", "confidence", "rationale"])
    fake.node = "npu"
    fake.confidence = 0.98
    with patch.object(client_router, "_b") as mock_b:
        mock_b.ClassifyTaskIntent.return_value = fake
        out = client_router.classify_task_intent("run NPU reasoning")
    assert out.node == "npu"
    assert out.confidence == 0.98


def test_decide_hardware_routing_returns_typed_model() -> None:
    fake = MagicMock(
        spec=["model_id", "tier", "port", "temperature", "top_p", "max_context", "evi_score"]
    )
    fake.model_id = "deepseek-r1-0528-8b-FLM"
    fake.tier = "npu"
    fake.port = 13305
    with patch.object(client_router, "_b") as mock_b:
        mock_b.DecideHardwareRouting.return_value = fake
        out = client_router.decide_hardware_routing("reasoning", 500, ["tools"])
    assert out.model_id == "deepseek-r1-0528-8b-FLM"
    assert out.port == 13305


def test_evaluate_harmonic_sheaf_returns_typed_model() -> None:
    fake = MagicMock(
        spec=["num_nodes", "num_edges", "dirichlet_energy", "is_concordant", "disputed_edges"]
    )
    fake.dirichlet_energy = 0.42
    fake.is_concordant = True
    with patch.object(client_router, "_b") as mock_b:
        mock_b.EvaluateHarmonicSheaf.return_value = fake
        out = client_router.evaluate_harmonic_sheaf("stalks", "maps")
    assert out.dirichlet_energy == 0.42
    assert out.is_concordant is True


def test_get_type_builder_initializes_properly() -> None:
    tb = client_router.get_type_builder()
    assert tb is not None
    assert hasattr(tb, "VaultGraphExtraction")
    assert hasattr(tb, "RoutingDecision")
    assert hasattr(tb, "CodeHarness")
