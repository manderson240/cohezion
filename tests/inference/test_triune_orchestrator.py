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
    assert "gaia:llama3.2-1b-FLM" in labels  # N2: NPU model is llama3.2-1b-FLM (42 TPS on XDNA2)
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


def test_build_triune_orchestrator_base_url_param():
    """base_url kwargs override individual tier endpoints (D refactor)."""
    captured: list[dict] = []

    def capturing_tier(model_id: str, base_url: str, **_kwargs):
        captured.append({"model_id": model_id, "base_url": base_url})
        return _mock_gaia_tier(model_id)

    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier",
        side_effect=capturing_tier,
    ):
        build_triune_orchestrator(
            npu_base_url="http://npu-host:9001",
            igpu_base_url="http://igpu-host:9002",
            cpu_base_url="http://cpu-host:9003",
        )

    assert captured[0]["base_url"] == "http://npu-host:9001/v1"
    assert captured[1]["base_url"] == "http://igpu-host:9002/v1"
    assert captured[2]["base_url"] == "http://cpu-host:9003/v1"


def test_build_triune_orchestrator_cpu_port_default_is_13309():
    """N2 invariant: cpu default is 13309 (Lemonade), not 11434 (Ollama)."""
    captured: list[dict] = []

    def capturing_tier(model_id: str, base_url: str, **_kwargs):
        captured.append({"model_id": model_id, "base_url": base_url})
        return _mock_gaia_tier(model_id)

    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier",
        side_effect=capturing_tier,
    ):
        build_triune_orchestrator()

    cpu_entry = next(c for c in captured if "31B" in c["model_id"])
    assert "13309" in cpu_entry["base_url"], (
        f"N2 violation: cpu_base_url should contain 13309, got {cpu_entry['base_url']}"
    )
