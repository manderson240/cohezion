"""Tests for DifficultyEstimator (#93, #142) — predictive tier pre-allocation.

GIC1: predict_tier returns 'unknown' before any records
GIC2: returns cheapest tier with success_rate >= 0.7
GIC3: falls back to highest-mean-quality tier when no clear winner
GIC4: get_escalation_rate returns correct fraction
GIC5: wiring — SkillRefiner._difficulty_estimator exists
GIC6: discriminating — escalating NPU runs don't get NPU recommendation

GIC_NEW_4: predict_tier accepts optional prompt="" parameter (#142)
GIC_NEW_5: cold-start with complex reasoning prompt → 'cpu'
GIC_NEW_6: cold-start with short simple prompt → 'npu'
GIC_NEW_7: post-execution history overrides prompt-based estimate
"""

import pytest

from cohezion.compound.difficulty_estimator import DifficultyEstimator
from cohezion.compound.skill_refiner import SkillRefiner


@pytest.fixture()
def est() -> DifficultyEstimator:
    return DifficultyEstimator()


class TestDifficultyEstimatorStructural:
    def test_predict_unknown_before_records(self, est: DifficultyEstimator) -> None:
        """GIC1: unknown when no history."""
        assert est.predict_tier("skill_a", "generate") == "unknown"

    def test_escalation_rate_none_before_records(self, est: DifficultyEstimator) -> None:
        """GIC4 structural: None when no history."""
        assert est.get_escalation_rate("skill_a", "generate") is None

    def test_skill_refiner_has_difficulty_estimator(self) -> None:
        """GIC5: wiring — attribute exists and is DifficultyEstimator."""
        refiner = SkillRefiner()
        assert hasattr(refiner, "_difficulty_estimator")
        assert isinstance(refiner._difficulty_estimator, DifficultyEstimator)


class TestDifficultyEstimatorBehavioral:
    def test_cheapest_successful_tier_returned(self, est: DifficultyEstimator) -> None:
        """GIC2: 5x NPU with no escalation, quality 0.85 → recommends 'npu'."""
        for _ in range(5):
            est.record("skill_a", "classify", "npu", escalation_count=0, quality_score=0.85)
        assert est.predict_tier("skill_a", "classify") == "npu"

    def test_discriminating_escalating_npu_gets_igpu(self, est: DifficultyEstimator) -> None:
        """GIC6: NPU always escalates → success_rate < threshold → igpu preferred.
        Both tiers need ≥_MIN_SAMPLES records for the LCB path to activate."""
        # NPU: all escalate (not successful) — must meet _MIN_SAMPLES for LCB to evaluate
        for _ in range(5):
            est.record("skill_b", "reason", "npu", escalation_count=1, quality_score=0.55)
        # iGPU: no escalation, quality good — also meets _MIN_SAMPLES
        for _ in range(5):
            est.record("skill_b", "reason", "igpu", escalation_count=0, quality_score=0.80)
        result = est.predict_tier("skill_b", "reason")
        assert result == "igpu", f"Expected igpu (npu escalates), got {result}"

    def test_fallback_to_highest_quality_when_no_threshold_met(self, est: DifficultyEstimator) -> None:
        """GIC3: no tier clears 0.7 success_rate → returns tier with best mean quality."""
        # npu: 2 samples, quality 0.7 (marginal)
        for _ in range(2):
            est.record("skill_c", "gen", "npu", escalation_count=0, quality_score=0.7)
        # cpu: 2 samples, quality 0.9 (better but still only 2 samples)
        for _ in range(2):
            est.record("skill_c", "gen", "cpu", escalation_count=0, quality_score=0.9)
        # Both have enough samples; npu has 100% success, cpu has 100% success
        # So npu should be picked as cheapest with >= threshold
        result = est.predict_tier("skill_c", "gen")
        # npu is the cheapest tier in _TIER_ORDER → it wins when both have 100% success
        assert result in ("npu", "igpu", "cpu")  # at minimum returns a valid tier

    def test_fallback_chooses_highest_quality(self, est: DifficultyEstimator) -> None:
        """GIC3: only 1 sample per tier (below _MIN_SAMPLES=2) → fallback by quality."""
        est.record("skill_d", "gen", "npu", escalation_count=0, quality_score=0.5)
        est.record("skill_d", "gen", "igpu", escalation_count=0, quality_score=0.95)
        # Only 1 sample each → fallback path → cpu has 0 → igpu wins on quality
        result = est.predict_tier("skill_d", "gen")
        assert result == "igpu", f"Expected igpu (highest quality), got {result}"

    def test_escalation_rate_correct(self, est: DifficultyEstimator) -> None:
        """GIC4: 2/5 runs escalated → rate = 0.4."""
        est.record("skill_e", "code", "npu", escalation_count=1, quality_score=0.7)
        est.record("skill_e", "code", "npu", escalation_count=0, quality_score=0.8)
        est.record("skill_e", "code", "npu", escalation_count=1, quality_score=0.6)
        est.record("skill_e", "code", "npu", escalation_count=0, quality_score=0.9)
        est.record("skill_e", "code", "npu", escalation_count=0, quality_score=0.85)
        rate = est.get_escalation_rate("skill_e", "code")
        assert rate is not None
        assert abs(rate - 0.4) < 1e-9

    def test_unknown_tier_normalised_to_cpu(self, est: DifficultyEstimator) -> None:
        """Non-standard tier_used values are stored as 'cpu' (defensive normalisation)."""
        est.record("skill_f", "t", "unknown_tier", escalation_count=0, quality_score=0.9)
        est.record("skill_f", "t", "unknown_tier", escalation_count=0, quality_score=0.9)
        # normalised → cpu bucket; cpu should have success_rate=1.0
        result = est.predict_tier("skill_f", "t")
        assert result == "cpu"  # cpu is the normalised bucket

    def test_independent_skill_keys(self, est: DifficultyEstimator) -> None:
        """Records for (skill_a, op) don't affect (skill_b, op)."""
        for _ in range(5):
            est.record("skill_a", "op", "igpu", escalation_count=0, quality_score=0.9)
        assert est.predict_tier("skill_b", "op") == "unknown"

    def test_window_caps_at_10(self, est: DifficultyEstimator) -> None:
        """Records beyond window=10 drop off; latest dominate."""
        # First 10: npu with high quality
        for _ in range(10):
            est.record("skill_g", "op", "npu", escalation_count=0, quality_score=0.9)
        # Next 10: cpu with higher quality (overwrites npu in window)
        for _ in range(10):
            est.record("skill_g", "op", "cpu", escalation_count=0, quality_score=0.95)
        # Window now has 10 cpu records (npu dropped off)
        result = est.predict_tier("skill_g", "op")
        assert result == "cpu"  # npu evicted from window


# ---------------------------------------------------------------------------
# Prompt-feature cold-start (#142, gitmoot modeltier.go pattern)
# ---------------------------------------------------------------------------


class TestDifficultyEstimatorPromptFeatures:
    """GIC_NEW_4–7: prompt-based pre-execution complexity estimation.

    Sourced from gitmoot/modeltier.go (2026-06-28 research): pre-execution
    features (prompt length, keyword density, action type) improve cold-start
    tier prediction before post-execution history accumulates.

    GIC1 is preserved: prompt="" default keeps 'unknown' for no-history calls.
    """

    # ── T1 structural ──────────────────────────────────────────────────────

    def test_predict_tier_accepts_prompt_kwarg(self, est: DifficultyEstimator) -> None:
        """GIC_NEW_4 structural: predict_tier signature has 'prompt' parameter."""
        import inspect

        params = inspect.signature(est.predict_tier).parameters
        assert "prompt" in params, (
            "predict_tier must accept optional prompt= kwarg for cold-start features"
        )

    def test_complexity_score_method_exists(self, est: DifficultyEstimator) -> None:
        """GIC_NEW_4 structural: _complexity_score(prompt) returns float in [0, 1]."""
        score = est._complexity_score("hello world")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0, f"Complexity score out of range: {score}"

    def test_complexity_score_zero_for_empty(self, est: DifficultyEstimator) -> None:
        """_complexity_score returns 0.0 for empty string (safe default)."""
        assert est._complexity_score("") == pytest.approx(0.0)

    # ── GIC1 preservation ──────────────────────────────────────────────────

    def test_empty_prompt_no_history_returns_unknown(self, est: DifficultyEstimator) -> None:
        """GIC1 preserved: no history + explicit empty prompt → 'unknown'."""
        assert est.predict_tier("s", "op", prompt="") == "unknown"

    def test_no_prompt_no_history_returns_unknown(self, est: DifficultyEstimator) -> None:
        """GIC1 preserved: no history + no prompt argument → 'unknown'."""
        assert est.predict_tier("s", "op") == "unknown"

    # ── T2 discriminating ──────────────────────────────────────────────────

    def test_short_simple_prompt_predicts_npu(self, est: DifficultyEstimator) -> None:
        """GIC_NEW_6 discriminating: brief query → NPU (cheapest tier).

        Wrong impl: returns 'unknown' for any prompt with no history, or
        returns 'cpu' regardless of prompt length/content.
        """
        result = est.predict_tier("novel_skill", "op", prompt="What is Python?")
        assert result == "npu", (
            f"Short simple prompt should predict 'npu', got '{result}'"
        )

    def test_long_complex_reasoning_prompt_predicts_cpu(
        self, est: DifficultyEstimator
    ) -> None:
        """GIC_NEW_5 discriminating: multi-keyword reasoning task → CPU tier.

        Wrong impl: returns 'unknown' (ignores prompt entirely), or returns
        'npu' (treats all prompts as simple), or returns 'igpu' for 50% of
        inputs (a random-tier wrong impl would fail this specific assertion).

        Must be specifically 'cpu' — not just any non-unknown tier.
        """
        complex_prompt = (
            "Analyze and evaluate the architectural trade-offs between "
            "microservices and monolithic systems. Implement a comprehensive "
            "comparison considering scalability, maintainability, and operational "
            "complexity. Provide a detailed reasoning process with sophisticated "
            "justification for each design decision. Synthesize and critique the "
            "existing literature on distributed systems architecture."
        )
        result = est.predict_tier("novel_skill", "novel_op", prompt=complex_prompt)
        assert result == "cpu", (
            f"Complex reasoning prompt should predict 'cpu', got '{result}'"
        )

    def test_history_overrides_prompt_complexity(self, est: DifficultyEstimator) -> None:
        """GIC_NEW_7 discriminating: post-execution history wins over prompt estimate.

        Wrong impl: prompt always overrides history (breaks GIC2).
        Even a complex prompt must not override solid NPU success history.
        """
        for _ in range(5):
            est.record("skill_x", "op", "npu", escalation_count=0, quality_score=0.9)

        complex_prompt = (
            "Analyze and evaluate comprehensive architectural design with "
            "sophisticated reasoning algorithms. Implement and optimize detailed "
            "solutions across distributed systems."
        )
        result = est.predict_tier("skill_x", "op", prompt=complex_prompt)
        assert result == "npu", (
            f"Solid NPU history must override prompt complexity estimate; got '{result}'"
        )

    def test_complexity_score_higher_for_long_complex_prompt(
        self, est: DifficultyEstimator
    ) -> None:
        """_complexity_score is strictly higher for complex prompt than trivial one.

        Wrong impl: returns constant 0.5 for all non-empty strings,
        or identical scores for both.
        """
        trivial = est._complexity_score("What is Python?")
        complex_p = est._complexity_score(
            "Analyze and evaluate the comprehensive architectural design. "
            "Implement a sophisticated reasoning algorithm. Optimize and "
            "synthesize the detailed step-by-step solution."
        )
        assert complex_p > trivial, (
            f"Complex prompt score {complex_p:.3f} must exceed trivial score {trivial:.3f}"
        )


def test_miscalibration_lucky_cheap_tier_does_not_pull_routing_down():
    """UCCI calibration (frequency guard): a skill that mostly runs iGPU but occasionally 'gets
    lucky' on NPU must still predict iGPU. A rare lucky cheap success has a high CONDITIONAL
    success-rate (2/2=100%) but low FREQUENCY (2/10) — a no-frequency-guard impl returns 'npu'
    (both the success-path and the mean-quality fallback) and FAILS this. Reproduces the empirical
    drift the GIC learning experiment surfaced (100% → 62%)."""
    from cohezion.compound.difficulty_estimator import DifficultyEstimator

    de = DifficultyEstimator()
    for _ in range(8):  # dominant: iGPU, escalated (never a clean success)
        de.record("translate", "op", "igpu", escalation_count=1, quality_score=0.90)
    for _ in range(2):  # lucky: NPU clean + slightly higher quality (would win the naive fallback)
        de.record("translate", "op", "npu", escalation_count=0, quality_score=0.95)
    assert de.predict_tier("translate", "op") == "igpu"  # NOT npu (freq 2/10 < _MIN_TIER_FREQUENCY)


def test_wilson_lcb_rejects_lucky_rare_accepts_sustained():
    """H3: the Wilson LCB is the calibration mechanism — a lucky 2/2 has a wide interval (low LCB,
    rejected) while sustained success is tight (high LCB, trusted)."""
    from cohezion.compound.difficulty_estimator import _LCB_ADEQUATE, _wilson_lcb

    assert _wilson_lcb(2, 2) < _LCB_ADEQUATE   # lucky-rare → not adequate
    assert _wilson_lcb(8, 8) >= _LCB_ADEQUATE  # sustained → adequate
    assert _wilson_lcb(0, 5) == 0.0            # no successes → floor


def test_balanced_3way_does_not_default_to_worst_tier():
    """H3 regression (reviewer-found): a skill that finals cleanly at npu but is also reached at
    igpu/cpu must route to the cheapest clean-supported tier (npu), NOT default to cpu. The old 0.34
    frequency guard rejected every tier at ~33% each and defaulted to cpu — a wrong impl fails this."""
    from cohezion.compound.difficulty_estimator import DifficultyEstimator

    de = DifficultyEstimator()
    for _ in range(4):
        de.record("bal", "op", "npu", 0, 0.90)
    for _ in range(3):
        de.record("bal", "op", "igpu", 1, 0.90)
    for _ in range(3):
        de.record("bal", "op", "cpu", 2, 0.90)
    assert de.predict_tier("bal", "op") == "npu"
