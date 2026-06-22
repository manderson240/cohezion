from unittest.mock import MagicMock, patch

from cohezion.inference.triune_orchestrator import build_triune_orchestrator


def _mock_gaia_tier(model_id: str, **_kwargs):
    tier = MagicMock()
    tier.label = f"gaia:{model_id}"
    return tier


def test_build_triune_orchestrator_structure():
    """Verify the orchestrator is built with 3 tiers."""
    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier", side_effect=_mock_gaia_tier
    ):
        orch = build_triune_orchestrator()
    assert len(orch.tiers) == 3
    labels = [tier[0].label for tier in orch.tiers]
    assert "gaia:llama3.2-1b-FLM" in labels
    assert "gaia:Gemma-4-E4B-it-GGUF" in labels
    assert "gaia:Gemma-4-31B-it-GGUF" in labels


def test_build_triune_orchestrator_quality_gates():
    """Verify the quality gates."""
    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier", side_effect=_mock_gaia_tier
    ):
        orch = build_triune_orchestrator()
    assert orch.tiers[0][1].min_chars == 500
    assert orch.tiers[1][1].min_chars == 2000
    assert orch.tiers[2][1].min_chars is None
