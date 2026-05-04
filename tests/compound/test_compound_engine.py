"""Tests for the unified CompoundEngine."""
from cohezion.compound.compound_engine import CompoundEngine


class TestCompoundEngine:

    def test_default_initialization(self):
        engine = CompoundEngine()
        assert engine.metrics is not None
        assert engine.score_window is not None
        assert engine.scheduler is not None

    def test_record_execution_updates_metrics(self):
        engine = CompoundEngine()
        engine.record_execution("E63", delta=0.15, coherence=0.8)
        summary = engine.get_summary()
        assert summary["session"]["n_experiments"] == 1
        assert summary["session"]["mean_delta"] == 0.15

    def test_record_score_updates_window(self):
        engine = CompoundEngine()
        for s in [0.6, 0.7, 0.8]:
            engine.record_score(s)
        summary = engine.get_summary()
        assert abs(summary["score_trend"]["mean"] - 0.7) < 0.001

    def test_get_summary_has_required_keys(self):
        engine = CompoundEngine()
        summary = engine.get_summary()
        assert "session" in summary
        assert "score_trend" in summary
        assert "scheduler" in summary
        assert "overall_health" in summary

    def test_overall_health_true_when_healthy(self):
        engine = CompoundEngine()
        for _ in range(5):
            engine.record_execution("E63", delta=0.15, coherence=0.8)
            engine.record_score(0.75)
        summary = engine.get_summary()
        assert summary["overall_health"] is True

    def test_get_next_experiments_returns_list(self):
        engine = CompoundEngine()
        exps = engine.get_next_experiments(n=3)
        assert len(exps) == 3
        assert all("hypothesis" in e for e in exps)

    def test_get_health_passes(self):
        engine = CompoundEngine()
        health = engine.get_health()
        assert health["healthy"] is True

