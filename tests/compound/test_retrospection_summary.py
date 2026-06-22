"""Tests for Retrospection Summaries (Story 5.4, FR18)."""

from __future__ import annotations

import pytest

from cohezion.compound.retrospection_summary import (
    CycleMetrics,
    FailureSignature,
    RetrospectionEngine,
    RetrospectionSummary,
    mine_failure_signatures,
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


@pytest.mark.unit
class TestFailureSignatureAndMining:
    """Self-Harness Weakness Mining: FailureSignature + mine_failure_signatures."""

    def _failed_summary(self, cycle_id: str, anomalies: list[str]) -> RetrospectionSummary:
        m = CycleMetrics(
            coherence_start=0.4,
            coherence_end=0.3,
            tokens_used=500,
            skill_name="test-skill",
            phase="executing",
            success=False,
            anomalies=anomalies,
        )
        return RetrospectionSummary(cycle_id=cycle_id, narrative="failed", metrics=m)

    def test_mine_returns_empty_for_all_successes(self):
        m = CycleMetrics(0.5, 0.7, 100, "s", "executing", True)
        summaries = [RetrospectionSummary(cycle_id="c1", narrative="ok", metrics=m)]
        assert mine_failure_signatures(summaries) == []

    def test_mine_extracts_one_signature_per_failure(self):
        s1 = self._failed_summary("c1", ["output_mismatch", "retry_loop"])
        s2 = self._failed_summary("c2", ["timeout", "missing_artifact"])
        sigs = mine_failure_signatures([s1, s2])
        assert len(sigs) == 2

    def test_terminal_cause_from_first_anomaly(self):
        s = self._failed_summary("c1", ["output_mismatch", "retry_loop"])
        sig = mine_failure_signatures([s])[0]
        assert sig.terminal_cause == "output_mismatch"

    def test_mechanism_from_second_anomaly(self):
        s = self._failed_summary("c1", ["output_mismatch", "retry_loop"])
        sig = mine_failure_signatures([s])[0]
        # discriminating: mechanism must be second anomaly, not first
        assert sig.agent_mechanism == "retry_loop"
        assert sig.agent_mechanism != "output_mismatch"

    def test_mechanism_falls_back_to_skill_name_when_single_anomaly(self):
        s = self._failed_summary("c1", ["output_mismatch"])
        sig = mine_failure_signatures([s])[0]
        assert sig.agent_mechanism == "test-skill"

    def test_signature_carries_cycle_id(self):
        s = self._failed_summary("my-cycle-123", ["err"])
        sig = mine_failure_signatures([s])[0]
        assert sig.cycle_id == "my-cycle-123"

    def test_failure_signature_is_dataclass(self):
        fs = FailureSignature(
            terminal_cause="t",
            causal_status="c",
            agent_mechanism="m",
            skill_name="s",
            cycle_id="cy",
        )
        assert fs.terminal_cause == "t"
