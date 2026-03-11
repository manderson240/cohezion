"""
Step 12 Integration Tests: Tip-of-the-Spear SLM Orchestration.

Verifies:
1. Model Ranking: Quality-first prioritization of local SOTA models.
2. Residency Awareness: Correct identification of Strix Halo substrate.
3. Local Preference: Zero-cost preference for Ollama models.
"""

from cohezion.reliability.residency_awareness import get_residency_anchors
from cohezion.swarm.model_ranker import ModelRanker


class TestSLMOrchestration:
    """Verifies the local-first, SOTA-driven swarm intelligence."""

    def test_quality_first_ranking(self):
        """Step 12.1: DeepSeek-R1 must be recognized as the highest quality reasoning model."""
        ranker = ModelRanker()

        # DeepSeek-R1 (8b) has the highest default coherence (0.95)
        ds_coherence = ranker._get_coherence_score("deepseek-r1:8b")
        qw_coherence = ranker._get_coherence_score("qwen3-coder:32b")

        assert ds_coherence > qw_coherence
        assert ds_coherence == 0.95

    def test_hardware_residency_awareness(self):
        """Step 12.2: System must correctly identify its Strix Halo substrate."""
        anchors = get_residency_anchors()

        assert "AMD RYZEN AI MAX+" in anchors["cpu"]
        assert anchors["ram_gb"] == 128
        assert anchors["os"] == "Linux"

    def test_local_model_zero_cost(self):
        """Step 12.3: Local Ollama models should report $0.00 cost."""
        ranker = ModelRanker()
        available = ["qwen3-coder:32b"]

        ranked = ranker.rank_models(available_models=available)
        assert ranked[0][1].cost_per_token == 0.0
