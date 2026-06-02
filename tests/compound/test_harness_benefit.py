"""Unit tests for HarnessBenefitTracker."""

from __future__ import annotations

import pytest

from cohezion.compound.harness_benefit import HarnessBenefitTracker


@pytest.mark.unit
class TestHarnessBenefitTracker:
    """Tests for tracking pre/post refinement quality metrics."""

    def setup_method(self) -> None:
        self.tracker = HarnessBenefitTracker()

    def test_record_pre_execution(self) -> None:
        """Verify pre-execution score is correctly logged."""
        self.tracker.record_pre_execution("test-skill", 0.70)
        record = self.tracker.get_record("test-skill")
        assert record is not None
        assert record.pre_refinement_score == 0.70
        assert record.post_refinement_score is None
        assert record.benefit_score is None

    def test_record_post_execution(self) -> None:
        """Verify post-execution score and metadata are logged."""
        self.tracker.record_post_execution(
            "test-skill",
            quality_score=0.85,
            model_tier="igpu",
            instruction_length_delta=120,
        )
        record = self.tracker.get_record("test-skill")
        assert record is not None
        assert record.post_refinement_score == 0.85
        assert record.model_tier == "igpu"
        assert record.instruction_length_delta == 120

    def test_benefit_score_calculation(self) -> None:
        """Verify benefit_score computes post_score - pre_score."""
        self.tracker.record_pre_execution("test-skill", 0.70)
        self.tracker.record_post_execution("test-skill", 0.85)
        record = self.tracker.get_record("test-skill")
        assert record is not None
        assert record.benefit_score == pytest.approx(0.15)

    def test_invocation_tracking(self) -> None:
        """Verify invocation count increments properly."""
        self.tracker.record_invocation("test-skill")
        record = self.tracker.get_record("test-skill")
        assert record is not None
        assert record.invocation_count == 1
        assert record.was_invoked is True

        self.tracker.record_invocation("test-skill")
        assert record.invocation_count == 2

    def test_zero_invocation_skills(self) -> None:
        """Verify tracking of skills refined but never called."""
        self.tracker.record_pre_execution("skill-a", 0.80)
        self.tracker.record_pre_execution("skill-b", 0.75)
        self.tracker.record_post_execution("skill-b", 0.80)

        # Record invocation only on skill-b
        self.tracker.record_invocation("skill-b")

        # skill-a was refined (has pre score) but never invoked
        assert "skill-a" in self.tracker.zero_invocation_skills()
        assert "skill-b" not in self.tracker.zero_invocation_skills()

    def test_harmful_refinements(self) -> None:
        """Verify detection of regressions (negative benefit)."""
        self.tracker.record_pre_execution("skill-a", 0.80)
        self.tracker.record_post_execution("skill-a", 0.75)  # regressed

        self.tracker.record_pre_execution("skill-b", 0.80)
        self.tracker.record_post_execution("skill-b", 0.85)  # improved

        assert "skill-a" in self.tracker.harmful_refinements()
        assert "skill-b" not in self.tracker.harmful_refinements()

    def test_summary_aggregations(self) -> None:
        """Verify aggregate statistics are computed accurately."""
        self.tracker.record_pre_execution("skill-a", 0.80)
        self.tracker.record_post_execution("skill-a", 0.75)

        self.tracker.record_pre_execution("skill-b", 0.80)
        self.tracker.record_post_execution("skill-b", 0.90)

        summary = self.tracker.summary()
        assert summary["total_tracked"] == 2
        assert summary["with_measured_benefit"] == 2
        assert summary["harmful_refinements"] == 1
        assert summary["mean_benefit"] == pytest.approx(0.025)
