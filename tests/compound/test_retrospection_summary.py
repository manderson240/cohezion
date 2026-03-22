"""Tests for Retrospection Summaries (Story 5.4, FR18)."""

from __future__ import annotations

import pytest

from cohezion.compound.retrospection_summary import (
    CycleMetrics,
    RetrospectionEngine,
)


def _make_metrics(**kwargs) -> CycleMetrics:
    defaults = {
        "coherence_start": 0.5,
        "coherence_end": 0.6,
        "tokens_used": 1200,
        "skill_name": "COMPOUND_ENGINEERING",
        "phase": "reflecting",
        "success": True,
    }
    defaults.update(kwargs)
    return CycleMetrics(**defaults)


class TestRetrospectionEngine:
    def test_summary_generates_narrative(self):
        """Summary contains a first-person narrative."""
        engine = RetrospectionEngine()
        summary = engine.summarize("cycle-1", _make_metrics())
        assert "I succeeded" in summary.narrative
        assert "COMPOUND_ENGINEERING" in summary.narrative

    def test_failed_cycle_narrative(self):
        """Failed cycles have different narrative tone."""
        engine = RetrospectionEngine()
        summary = engine.summarize("cycle-2", _make_metrics(success=False))
        assert "encountered challenges" in summary.narrative

    def test_coherence_improvement_insight(self):
        """Strong improvement generates positive insight."""
        engine = RetrospectionEngine()
        summary = engine.summarize(
            "cycle-3",
            _make_metrics(coherence_start=0.3, coherence_end=0.6),
        )
        assert any("improvement" in i for i in summary.insights)

    def test_coherence_degradation_insight(self):
        """Degradation generates rollback suggestion."""
        engine = RetrospectionEngine()
        summary = engine.summarize(
            "cycle-4",
            _make_metrics(coherence_start=0.7, coherence_end=0.4),
        )
        assert any("degradation" in i for i in summary.insights)

    def test_high_token_usage_insight(self):
        """High token usage generates decomposition suggestion."""
        engine = RetrospectionEngine()
        summary = engine.summarize(
            "cycle-5",
            _make_metrics(tokens_used=8000),
        )
        assert any("token" in i.lower() for i in summary.insights)

    def test_anomaly_detection(self):
        """Anomalies are reported in narrative and insights."""
        engine = RetrospectionEngine()
        summary = engine.summarize(
            "cycle-6",
            _make_metrics(anomalies=["coherence_spike", "thermal_warning"]),
        )
        assert "anomalies" in summary.narrative.lower()
        assert any("anomal" in i.lower() for i in summary.insights)

    def test_summaries_accumulate(self):
        """Engine tracks all summaries."""
        engine = RetrospectionEngine()
        for i in range(3):
            engine.summarize(f"cycle-{i}", _make_metrics())
        assert len(engine.summaries) == 3

    def test_get_recent(self):
        """Recent summaries returns last N."""
        engine = RetrospectionEngine()
        for i in range(10):
            engine.summarize(f"cycle-{i}", _make_metrics())
        recent = engine.get_recent(3)
        assert len(recent) == 3
        assert recent[-1]["cycle_id"] == "cycle-9"

    def test_serialization(self):
        """Summary serializes to dict with all fields."""
        engine = RetrospectionEngine()
        summary = engine.summarize("cycle-s", _make_metrics())
        d = summary.to_dict()
        assert "narrative" in d
        assert "coherence_delta" in d
        assert d["coherence_delta"] == pytest.approx(0.1)
