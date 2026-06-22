"""Tests for SkillRefinementValidator — before/after skill mutation performance gating."""

import pytest

from cohezion.compound.skill_refinement_validator import RefinementMetrics, SkillRefinementValidator


def _metrics(
    success_rate: float = 0.9,
    avg_latency_ms: float = 100.0,
    avg_coherence: float = 0.8,
    sample_count: int = 10,
) -> RefinementMetrics:
    return RefinementMetrics(
        success_rate=success_rate,
        avg_latency_ms=avg_latency_ms,
        avg_coherence=avg_coherence,
        sample_count=sample_count,
        measured_at=RefinementMetrics.now_iso(),
    )


@pytest.fixture
def validator() -> SkillRefinementValidator:
    return SkillRefinementValidator(min_samples=5, max_degradation_pct=5.0)


@pytest.mark.unit
class TestSkillRefinementValidator:
    def test_baseline_recording(self, validator: SkillRefinementValidator) -> None:
        baseline = _metrics(success_rate=0.85)
        validator.record_baseline("my_skill", baseline)

        report = validator.get_improvement_report("my_skill")
        assert report["skill_name"] == "my_skill"
        assert report["baseline"]["success_rate"] == pytest.approx(0.85)
        assert "error" not in report

    def test_improvement_approved(self, validator: SkillRefinementValidator) -> None:
        validator.record_baseline("my_skill", _metrics(success_rate=0.80, avg_coherence=0.70))
        post = _metrics(success_rate=0.90, avg_coherence=0.80)

        approved, reason = validator.validate_refinement("my_skill", post)

        assert approved is True
        assert reason == "improved"

    def test_degradation_blocked_success_rate(self, validator: SkillRefinementValidator) -> None:
        validator.record_baseline("my_skill", _metrics(success_rate=0.90))
        post = _metrics(success_rate=0.80)  # 10% drop, exceeds 5% threshold

        approved, reason = validator.validate_refinement("my_skill", post)

        assert approved is False
        assert "success_rate" in reason
        assert "degraded" in reason

    def test_coherence_degradation_blocked(self, validator: SkillRefinementValidator) -> None:
        validator.record_baseline("my_skill", _metrics(avg_coherence=0.80))
        post = _metrics(avg_coherence=0.70)  # 0.10 drop, exceeds 0.05 threshold

        approved, reason = validator.validate_refinement("my_skill", post)

        assert approved is False
        assert "coherence" in reason
        assert "degraded" in reason

    def test_insufficient_samples_blocked(self, validator: SkillRefinementValidator) -> None:
        validator.record_baseline("my_skill", _metrics())
        post = _metrics(sample_count=3)  # below min_samples=5

        approved, reason = validator.validate_refinement("my_skill", post)

        assert approved is False
        assert "insufficient samples" in reason

    def test_no_baseline_blocked(self, validator: SkillRefinementValidator) -> None:
        post = _metrics()

        approved, reason = validator.validate_refinement("unknown_skill", post)

        assert approved is False
        assert "no baseline" in reason

    def test_marginal_degradation_within_threshold_approved(
        self, validator: SkillRefinementValidator
    ) -> None:
        # 3% drop is within the 5% threshold — should be approved
        validator.record_baseline("my_skill", _metrics(success_rate=0.90, avg_coherence=0.80))
        post = _metrics(success_rate=0.873, avg_coherence=0.771)

        approved, reason = validator.validate_refinement("my_skill", post)

        assert approved is True
        assert reason == "improved"

    def test_report_missing_skill_returns_error(self, validator: SkillRefinementValidator) -> None:
        report = validator.get_improvement_report("nonexistent")
        assert "error" in report
        assert report["skill_name"] == "nonexistent"


@pytest.mark.unit
class TestSplitGate:
    """Self-Harness split-wise regression gate (arXiv 2606.09498 §3.3)."""

    @pytest.fixture
    def v(self) -> SkillRefinementValidator:
        v = SkillRefinementValidator()
        v.record_baseline("sk", _metrics(success_rate=0.5))
        return v

    def test_both_improve_approved(self, v):
        approved, reason = v.validate_split_gate(
            "sk", _metrics(success_rate=0.7), _metrics(success_rate=0.6)
        )
        assert approved is True
        assert "Δin=+20.0%" in reason

    def test_held_in_degraded_rejected(self, v):
        approved, reason = v.validate_split_gate(
            "sk", _metrics(success_rate=0.4), _metrics(success_rate=0.6)
        )
        assert approved is False
        assert "held-in degraded" in reason

    def test_held_out_degraded_rejected(self, v):
        approved, reason = v.validate_split_gate(
            "sk", _metrics(success_rate=0.6), _metrics(success_rate=0.4)
        )
        assert approved is False
        assert "held-out degraded" in reason

    def test_no_improvement_on_either_split_rejected(self, v):
        # Both equal to baseline — max(Δin, Δho) == 0
        approved, reason = v.validate_split_gate(
            "sk", _metrics(success_rate=0.5), _metrics(success_rate=0.5)
        )
        assert approved is False
        assert "no improvement" in reason

    def test_no_baseline_rejected(self):
        v = SkillRefinementValidator()
        approved, reason = v.validate_split_gate("unknown", _metrics(), _metrics())
        assert approved is False
        assert "no baseline" in reason

    def test_discriminating_held_out_must_not_degrade(self, v):
        # Wrong impl: only checks held-in. This test catches it because held-out degrades.
        approved, _ = v.validate_split_gate(
            "sk", _metrics(success_rate=0.9), _metrics(success_rate=0.3)
        )
        assert approved is False  # held-out degraded by 20%
