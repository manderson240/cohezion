"""Tests for QuadratureNexus.apply_mycelium_feedback — E57 additive compounding fix.

These tests codify the findings from autoresearch experiments E55-E62:
  E55: Mycelium synthesis lifts consensus by +0.0625 at lr=1.0
  E56: OLD SET semantics caused cycle 2 to decay (root cause fixed here)
  E57: Additive calibration produces monotonic compounding toward 0.85
  E58: Production QuadratureNexus uses additive_calibration mechanism
  E59: Convergence formula: consensus_n = 0.85 - 0.125 * (1 - lr/2)^n
"""

from __future__ import annotations

import pytest

from cohezion.swarm.quadrature_nexus import QuadratureNexus, QuadratureProposal, VoiceType


@pytest.fixture
def nexus() -> QuadratureNexus:
    return QuadratureNexus()


@pytest.fixture
def proposal() -> QuadratureProposal:
    return QuadratureProposal(
        action="test_feedback",
        description="Deploy scheduled system update",
        context={"budget_available": False},
        submitted_by="test",
        priority=0.50,
    )


def _simple_skill(consensus: float, voice_mean: float = 0.725) -> str:
    """Build a synthesized skill string in the format produced by _synthesize_evo_deliberation_skill.

    apply_mycelium_feedback parses:
      - consensus=X.XXX from embedded entry content
      - '{voice}: mean_score=X.XXXX' for per-voice adjustments
    """
    return "\n".join(
        [
            "# EVO_DELIBERATION Skill (Auto-Synthesized from Nexus Journeys)",
            "",
            "## Per-Voice Mean Scores (E6 feedback)",
            f"- architect: mean_score={voice_mean:.4f}",
            f"- engineer: mean_score={voice_mean:.4f}",
            f"- ethicist: mean_score={voice_mean:.4f}",
            f"- resource: mean_score={voice_mean:.4f}",
            "",
            "## Extracted Patterns",
            f"- EVO test: evo_coherence=0.450 consensus={consensus:.4f} approved=1 "
            f"voice_scores=[architect={voice_mean:.3f} engineer={voice_mean:.3f} "
            f"ethicist={voice_mean:.3f} resource={voice_mean:.3f}] lifetime=10 marks=[directive]",
        ]
    )


class TestApplyMyceliumFeedbackInit:
    def test_mycelium_calibration_in_init(self, nexus: QuadratureNexus) -> None:
        """E57: _mycelium_calibration must be initialized in __init__, not dynamically."""
        assert hasattr(nexus, "_mycelium_calibration"), "_mycelium_calibration missing from __init__"
        for vt in VoiceType:
            assert nexus._mycelium_calibration[vt] == 0.0

    def test_score_adjustments_in_init(self, nexus: QuadratureNexus) -> None:
        for vt in VoiceType:
            assert nexus._score_adjustments[vt] == 0.0


class TestApplyMyceliumFeedbackMechanism:
    def test_mechanism_is_additive_calibration(self, nexus: QuadratureNexus) -> None:
        """E58: mechanism field must be 'additive_calibration', not 'score_injection'."""
        skill = _simple_skill(0.725)
        result = nexus.apply_mycelium_feedback(skill, learning_rate=1.0)
        assert result["mechanism"] == "additive_calibration"

    def test_cumulative_field_present(self, nexus: QuadratureNexus) -> None:
        """E58: adjustments dict must include 'cumulative' key."""
        skill = _simple_skill(0.725)
        result = nexus.apply_mycelium_feedback(skill, learning_rate=1.0)
        for voice_data in result["adjustments"].values():
            assert "cumulative" in voice_data

    def test_score_adjustments_equals_calibration(self, nexus: QuadratureNexus) -> None:
        """After feedback, _score_adjustments must equal _mycelium_calibration."""
        skill = _simple_skill(0.725)
        nexus.apply_mycelium_feedback(skill, learning_rate=1.0)
        for vt in VoiceType:
            assert nexus._score_adjustments[vt] == pytest.approx(nexus._mycelium_calibration[vt])


class TestApplyMyceliumFeedbackCompounding:
    def test_cycle2_does_not_decay(self, nexus: QuadratureNexus) -> None:
        """E56/E57: Second cycle must ADD to calibration, not replace it (E56 root cause).

        Old behavior (SET): cycle2_cal < cycle1_cal → consensus decays
        New behavior (+=): cycle2_cal > cycle1_cal → consensus compounds
        """
        # Cycle 1: from baseline 0.725, calibration rises to ~0.0625 per voice
        skill1 = _simple_skill(consensus=0.725, voice_mean=0.725)
        nexus.apply_mycelium_feedback(skill1, learning_rate=1.0)
        cal_after_cycle1 = sum(nexus._mycelium_calibration.values())
        assert cal_after_cycle1 > 0.0, "Cycle 1 produced no calibration"

        # Cycle 2: voice_mean is now baseline + calibration_per_voice ≈ 0.7875
        cal_per_voice_1 = next(iter(nexus._mycelium_calibration.values()))
        cycle2_voice_mean = 0.725 + cal_per_voice_1
        skill2 = _simple_skill(consensus=cycle2_voice_mean, voice_mean=cycle2_voice_mean)
        nexus.apply_mycelium_feedback(skill2, learning_rate=1.0)
        cal_after_cycle2 = sum(nexus._mycelium_calibration.values())

        assert cal_after_cycle2 > cal_after_cycle1, (
            f"E56 regression: calibration decreased from {cal_after_cycle1:.4f} "
            f"to {cal_after_cycle2:.4f} (SET semantics returned)"
        )

    def test_monotonic_compounding_over_5_cycles(self, nexus: QuadratureNexus) -> None:
        """E57: 5 cycles of additive compounding must be monotonically non-decreasing."""
        baseline_consensus = 0.725
        prev_cal = 0.0

        for cycle in range(5):
            cal_per_voice = next(iter(nexus._mycelium_calibration.values())) if nexus._mycelium_calibration else 0.0
            current_consensus = baseline_consensus + cal_per_voice
            current_voice_mean = baseline_consensus + cal_per_voice
            skill = _simple_skill(consensus=current_consensus, voice_mean=current_voice_mean)
            nexus.apply_mycelium_feedback(skill, learning_rate=1.0)
            curr_cal = sum(nexus._mycelium_calibration.values())
            assert curr_cal >= prev_cal - 1e-9, (
                f"Cycle {cycle + 1}: calibration decreased from {prev_cal:.5f} to {curr_cal:.5f}"
            )
            prev_cal = curr_cal

    def test_calibration_converges_toward_gap(self, nexus: QuadratureNexus) -> None:
        """E59: After many cycles, calibration converges toward gap_0 = 0.85 - 0.725 = 0.125."""
        gap_0 = 0.125  # 0.85 - 0.725

        baseline = 0.725
        for _ in range(30):
            cal = next(iter(nexus._mycelium_calibration.values())) if nexus._mycelium_calibration else 0.0
            current = baseline + cal
            skill = _simple_skill(consensus=current, voice_mean=current)
            nexus.apply_mycelium_feedback(skill, learning_rate=1.0)

        final_cal = next(iter(nexus._mycelium_calibration.values()))
        # After 30 cycles at lr=1.0, cal should be within 0.2% of gap_0
        assert abs(final_cal - gap_0) < 0.002, f"Calibration {final_cal:.5f} did not converge toward gap_0={gap_0}"


class TestApplyMyceliumFeedbackE5Goal:
    def test_single_cycle_lifts_consensus(self, nexus: QuadratureNexus) -> None:
        """E55: One synthesis cycle at lr=1.0 must lift consensus by >= 0.05."""
        skill = _simple_skill(consensus=0.725, voice_mean=0.725)
        nexus.apply_mycelium_feedback(skill, learning_rate=1.0)

        # calibration_per_voice = gap * 0.5 * lr = 0.125 * 0.5 * 1.0 = 0.0625
        calibration_per_voice = next(iter(nexus._mycelium_calibration.values()))
        delta = calibration_per_voice  # consensus delta = calibration_per_voice

        assert delta >= 0.05, f"E55 regression: single-cycle delta={delta:.4f} < 0.05"

    def test_lr2_crosses_threshold(self, nexus: QuadratureNexus) -> None:
        """E60: At lr=2.0, one synthesis cycle from baseline 0.725 reaches approval threshold 0.85."""
        skill = _simple_skill(consensus=0.725, voice_mean=0.725)
        nexus.apply_mycelium_feedback(skill, learning_rate=2.0)

        # Post consensus = baseline (0.725) + calibration per voice (≈ 0.125 at lr=2.0)
        calibration_per_voice = next(iter(nexus._mycelium_calibration.values()))
        post_consensus = 0.725 + calibration_per_voice
        assert post_consensus >= 0.85 - 1e-6, (
            f"E60 regression: lr=2.0 post_consensus={post_consensus:.4f} < 0.85 "
            f"(calibration_per_voice={calibration_per_voice:.5f})"
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_lifts_deliberation(self) -> None:
        """E62: Full E3/E6 pipeline (real EVO journeys → synthesis → feedback) improves consensus."""
        from cohezion.learning.mycelium_registry import MyceliumRegistry

        nexus = QuadratureNexus()
        proposal = QuadratureProposal(
            action="e62_pipeline_test",
            description="Deploy scheduled system update",
            context={"budget_available": False},
            submitted_by="test",
            priority=0.50,
        )

        # Phase A: collect real deliberation results
        baseline_scores: list[float] = []
        real_metadata: list[dict] = []
        for _ in range(8):
            result = await nexus.deliberate(proposal)
            baseline_scores.append(result.consensus_score)
            evo = nexus._evo_registry.get(proposal.action)
            real_metadata.append(
                {
                    "evo_biography": evo.to_dict() if evo else {},
                    "voice_scores": {r.voice.value.lower(): r.approval_score for r in result.responses},
                    "consensus_score": result.consensus_score,
                    "approved": result.approved,
                }
            )

        mean_baseline = sum(baseline_scores) / len(baseline_scores)

        # Synthesize from real EVO journeys
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        ingested = registry.ingest_evo_journeys(real_metadata)
        assert ingested >= 1, "ingest_evo_journeys returned 0"
        registry.run_audit()
        assert registry.skills, "run_audit produced no skills"

        skill = next(iter(registry.skills.values())).skill_content
        feedback = nexus.apply_mycelium_feedback(skill, learning_rate=1.0)
        assert feedback["mechanism"] == "additive_calibration"

        # Phase B: post deliberations
        post_proposal = QuadratureProposal(
            action="e62_pipeline_test_post",
            description="Deploy scheduled system update",
            context={"budget_available": False},
            submitted_by="test",
            priority=0.50,
        )
        post_scores: list[float] = []
        for _ in range(8):
            result = await nexus.deliberate(post_proposal)
            post_scores.append(result.consensus_score)

        mean_post = sum(post_scores) / len(post_scores)
        assert mean_post > mean_baseline, f"E62 regression: post={mean_post:.4f} ≤ baseline={mean_baseline:.4f}"
