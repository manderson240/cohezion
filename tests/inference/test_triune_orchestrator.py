import pytest
from cohezion.inference.triune_orchestrator import build_triune_orchestrator

def test_build_triune_orchestrator_structure():
    """Verify the orchestrator is built with 3 tiers."""
    orch = build_triune_orchestrator()
    assert len(orch.tiers) == 3
    labels = [tier[0].label for tier in orch.tiers]
    assert "gaia:qwen3.5-4b-FLM" in labels
    assert "gaia:Gemma-4-E4B-it-GGUF" in labels
    assert "gaia:Gemma-4-31B-it-GGUF" in labels

def test_build_triune_orchestrator_quality_gates():
    """Verify the quality gates."""
    orch = build_triune_orchestrator()
    assert orch.tiers[0][1].min_chars == 500
    assert orch.tiers[1][1].min_chars == 2000
    assert orch.tiers[2][1].min_chars is None
