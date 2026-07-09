"""Unit tests for evaluation_harness — standardized compound loop experiment metrics."""

from __future__ import annotations


from cohezion.inference.evaluation_harness import ExperimentMetrics


class TestExperimentMetrics:
    def test_default_values_are_zero(self):
        """All numeric fields default to 0."""
        m = ExperimentMetrics()
        assert m.tokens_per_sec == 0.0
        assert m.quality_score == 0.0
        assert m.total_tokens == 0
        assert m.error_count == 0
        assert m.estimated_cost_usd == 0.0

    def test_efficiency_score_zero_when_no_tokens(self):
        """efficiency_score returns 0 when total_tokens == 0 (no division by zero)."""
        m = ExperimentMetrics(quality_score=1.0, tokens_per_sec=100.0, total_tokens=0)
        assert m.efficiency_score() == 0.0

    def test_efficiency_score_proportional_to_quality(self):
        """Higher quality → higher efficiency score."""
        low = ExperimentMetrics(quality_score=0.5, tokens_per_sec=100, total_tokens=1000)
        high = ExperimentMetrics(quality_score=1.0, tokens_per_sec=100, total_tokens=1000)
        assert high.efficiency_score() > low.efficiency_score()

    def test_efficiency_score_proportional_to_throughput(self):
        """Higher tokens/sec → higher efficiency (same quality, same tokens)."""
        slow = ExperimentMetrics(quality_score=1.0, tokens_per_sec=50, total_tokens=1000)
        fast = ExperimentMetrics(quality_score=1.0, tokens_per_sec=200, total_tokens=1000)
        assert fast.efficiency_score() > slow.efficiency_score()

    def test_to_dict_structure(self):
        """to_dict returns correctly structured dict with all required sections."""
        m = ExperimentMetrics(
            tokens_per_sec=150.0,
            latency_ms=200.0,
            quality_score=0.9,
            success_rate=0.95,
            total_tokens=500,
        )
        d = m.to_dict()
        assert "throughput" in d
        assert "quality" in d
        assert "efficiency" in d
        assert "cost" in d
        assert "metadata" in d

    def test_to_dict_values_match(self):
        """to_dict values match the dataclass fields."""
        m = ExperimentMetrics(
            tokens_per_sec=200.0,
            quality_score=0.8,
            total_tokens=1000,
            estimated_cost_usd=0.01,
            notes="test run",
        )
        d = m.to_dict()
        assert d["throughput"]["tokens_per_sec"] == 200.0
        assert d["quality"]["quality_score"] == 0.8
        assert d["cost"]["estimated_usd"] == 0.01
        assert d["metadata"]["notes"] == "test run"

    def test_efficiency_score_in_to_dict(self):
        """to_dict includes the computed efficiency_score."""
        m = ExperimentMetrics(quality_score=1.0, tokens_per_sec=100, total_tokens=1000)
        d = m.to_dict()
        assert d["efficiency"]["efficiency_score"] == m.efficiency_score()
        assert d["efficiency"]["efficiency_score"] > 0

    def test_timestamp_auto_populated(self):
        """timestamp field is auto-populated (not empty string)."""
        m = ExperimentMetrics()
        assert m.timestamp != ""
        assert "T" in m.timestamp  # ISO format check

    def test_compound_loop_typical_metrics(self):
        """Simulate a typical compound loop iteration metric snapshot."""
        m = ExperimentMetrics(
            tokens_per_sec=42.0,  # NPU llama3.2-1b-FLM measured TPS
            latency_ms=393.0,  # NPU TTFT measured
            tokens_generated=20,  # typical NPU short-answer output
            quality_score=0.9,
            success_rate=1.0,
            total_tokens=20,
            notes="NPU routing: llama3.2-1b-FLM on short_categorical task",
        )
        assert m.efficiency_score() > 0
        score = m.efficiency_score()
        # Verify the formula: (quality * tps) / (total_tokens / 1000)
        expected = (0.9 * 42.0) / (20 / 1000)
        assert abs(score - expected) < 1e-6
