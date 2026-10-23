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


def test_build_triune_omni_orchestrator_three_tier_cascade():
    """The :13305 OmniRouter triune cascade (restored 2026-06-29 — make_executor's exec_provider)."""
    import pytest

    pytest.importorskip("gaia")  # GAIA LemonadeClient path
    from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

    orch = build_triune_omni_orchestrator()
    assert len(orch.tiers) == 3  # NPU -> iGPU -> CPU, all via :13305


def test_tr1_omni_orchestrator_tiers_use_model_card_temperature_not_zero():
    """TR1 (2026-07-07 goal: right model, right recipe): build_triune_omni_orchestrator used to
    hardcode temperature=0.0 for every tier via build_gaia_llm_tier's old default. Each tier must
    now resolve its own model's card temperature instead of one fixed value for all three."""
    import pytest

    pytest.importorskip("gaia")
    from cohezion.inference.model_card_defaults import get_sampling_defaults
    from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

    orch = build_triune_omni_orchestrator()
    temps = [tier[0].agent._temperature for tier in orch.tiers]
    # Each tier's temperature is ITS model's card value (never a fixed 0.0). With the default
    # tier 0 (Gemma-4-E2B since 2026-10-23) all three tiers are Gemma-4 cards, so all are 1.0;
    # the per-model check below is what distinguishes card resolution from one hardcoded value.
    assert temps == [1.0, 1.0, 1.0]  # Gemma-4-E2B (tier 0), Gemma-4-E4B (iGPU), Gemma-4-E2B (CPU)
    for tier, _gate in orch.tiers:
        card = get_sampling_defaults(tier.agent._model)["temperature"]
        assert tier.agent._temperature == card, tier.agent._model
    assert 0.0 not in temps
    igpu_extra = orch.tiers[1][0].agent._extra_sampling
    # reasoning_format="none" is added for Gemma-4 (a llamacpp thinking model) by the
    # thinking-model empty-output fix (ae3c1f677) so the tier returns non-empty content.
    assert igpu_extra == {"top_k": 64, "top_p": 0.95, "reasoning_format": "none"}
