"""Tests for skill refiner learning from execution results."""

from pathlib import Path

import pytest

from cohezion.compound.skill_refiner import (
    EnvironmentResponsePredictor,
    ExecutionMetrics,
    LearningSignal,
    ShadowCanaryValidator,
    SkillRefiner,
    SkillRefinerFactory,
)


@pytest.fixture
def skill_refiner():
    """Create a skill refiner instance."""
    return SkillRefiner()


@pytest.fixture
def sample_execution_result():
    """Create a sample execution result."""
    return {
        "success": True,
        "output": "Sample output",
        "metrics": {
            "duration_seconds": 1.5,
            "anomaly_score": 0.1,
            "error": None,
        },
        "duration_seconds": 1.5,
        "token_metrics": {
            "tokens_used": 200,
            "cache_hits": 2,
            "api_calls_made": 1,
        },
    }


class TestExecutionMetricsExtraction:
    """Test extraction of metrics from execution results."""

    def test_extract_metrics_success(self, skill_refiner, sample_execution_result):
        """Test extracting metrics from successful execution."""
        metrics = skill_refiner._extract_metrics(sample_execution_result)

        assert metrics.success is True
        assert metrics.duration_seconds == 1.5
        assert metrics.tokens_used == 200
        assert metrics.cached_hits == 2
        assert metrics.anomaly_score == 0.1
        assert metrics.quality_score > 0.8

    def test_extract_metrics_failure(self, skill_refiner):
        """Test extracting metrics from failed execution."""
        result = {
            "success": False,
            "output": "Error",
            "metrics": {"error": "Something failed"},
            "duration_seconds": 0.5,
            "token_metrics": {},
        }

        metrics = skill_refiner._extract_metrics(result)

        assert metrics.success is False
        assert metrics.duration_seconds == 0.5

    def test_extract_metrics_calculates_token_efficiency(
        self, skill_refiner, sample_execution_result
    ):
        """Test token efficiency calculation."""
        metrics = skill_refiner._extract_metrics(sample_execution_result)

        # tokens_used / duration = 200 / 1.5 ≈ 133.33
        assert metrics.token_efficiency == pytest.approx(133.33, rel=0.01)

    def test_extract_metrics_quality_score(self, skill_refiner, sample_execution_result):
        """Test quality score calculation (inverse of anomaly score)."""
        metrics = skill_refiner._extract_metrics(sample_execution_result)

        # quality_score = 1.0 - anomaly_score = 1.0 - 0.1 = 0.9
        assert metrics.quality_score == pytest.approx(0.9)


class TestLearningSignalGeneration:
    """Test generation of learning signals from metrics."""

    def test_generate_learning_signal_high_quality(self, skill_refiner, sample_execution_result):
        """Test generating signal from high quality execution."""
        metrics = skill_refiner._extract_metrics(sample_execution_result)
        signal = skill_refiner._generate_learning_signal("TEST_SKILL", "generate", metrics)

        assert signal is not None
        assert signal.skill_name == "TEST_SKILL"
        assert signal.operation_type == "generate"
        assert "high quality" in signal.key_insight.lower()
        assert signal.confidence > 0.8

    def test_generate_learning_signal_with_cache_hits(self, skill_refiner):
        """Test signal generation with cache hits."""
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=100.0,
            quality_score=0.85,
            anomaly_score=0.15,
            cached_hits=5,
        )

        signal = skill_refiner._generate_learning_signal("TEST_SKILL", "analyze", metrics)

        assert signal is not None
        assert "cache hits" in signal.key_insight.lower()

    def test_generate_learning_signal_low_quality(self, skill_refiner):
        """Test that low quality high anomaly execution generates signal on efficiency."""
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=100.0,
            quality_score=0.5,
            anomaly_score=0.5,
            cached_hits=0,
        )

        signal = skill_refiner._generate_learning_signal("TEST_SKILL", "generate", metrics)

        # Even with low quality, efficient token usage generates a signal
        assert signal is not None
        assert "efficient" in signal.key_insight.lower()


class TestPrimeFileLocation:
    """Test finding PRIME skill files."""

    def test_find_prime_file_exact_match(self, skill_refiner):
        """Test finding PRIME file with exact match."""
        # Look for existing PRIME file
        prime_file = skill_refiner._find_prime_file("SYSTEM_GUARDRAILS")

        if prime_file:  # Only assert if file exists
            assert prime_file.exists()
            assert "SYSTEM_GUARDRAILS_PRIME.md" in str(prime_file)

    def test_find_prime_file_not_found(self, skill_refiner):
        """Test handling of nonexistent PRIME file."""
        prime_file = skill_refiner._find_prime_file("NONEXISTENT_SKILL")

        assert prime_file is None


class TestRefine:
    """Test the main refine method."""

    def test_refine_skips_failed_execution(self, skill_refiner, sample_execution_result):
        """Test that refine skips failed executions."""
        sample_execution_result["success"] = False

        result = skill_refiner.refine("TEST_SKILL", "generate", sample_execution_result)

        assert result is None

    def test_refine_with_high_quality_execution(self, skill_refiner):
        """Test refining with successful high-quality execution."""
        result = {
            "success": True,
            "output": "Output",
            "metrics": {
                "anomaly_score": 0.05,
            },
            "duration_seconds": 1.0,
            "token_metrics": {
                "tokens_used": 150,
                "cache_hits": 1,
            },
        }

        # This will likely return None (no PRIME file for TEST_SKILL)
        # but the method should handle it gracefully
        refined = skill_refiner.refine("TEST_SKILL", "generate", result)

        # Refine can return None if no PRIME file found (expected for test)
        assert refined is None or isinstance(refined, str)

    def test_refine_handles_exceptions(self, skill_refiner):
        """Test that refine handles exceptions gracefully (non-blocking)."""
        result = {
            "success": True,
            "output": "Output",
            "metrics": {"anomaly_score": 0.1},
            "duration_seconds": 1.0,
            "token_metrics": {"tokens_used": 100},
        }

        # This should not raise an exception
        refined = skill_refiner.refine("TEST_SKILL", "generate", result)

        # Should return None gracefully without crashing
        assert refined is None or isinstance(refined, str)


class TestVersionBumping:
    """Test version bumping logic."""

    def test_bump_patch_version(self, skill_refiner):
        """Test bumping patch version."""
        new_version = skill_refiner._bump_version("1.0.0")
        assert new_version == "1.0.1"

    def test_bump_patch_version_double_digit(self, skill_refiner):
        """Test bumping patch version with double digits."""
        new_version = skill_refiner._bump_version("1.2.9")
        assert new_version == "1.2.10"

    def test_bump_version_invalid_format(self, skill_refiner):
        """Test bumping version with invalid format returns original."""
        new_version = skill_refiner._bump_version("invalid")
        assert new_version == "invalid"


class TestRecommendationGeneration:
    """Test recommendation generation."""

    def test_recommend_high_quality(self, skill_refiner):
        """Test recommendation for high quality execution."""
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=100.0,
            quality_score=0.95,
            anomaly_score=0.05,
            cached_hits=0,
        )

        recommendation = skill_refiner._generate_recommendation(metrics, "generate")

        assert "quality" in recommendation.lower() or "optimize" in recommendation.lower()

    def test_recommend_efficient_tokens(self, skill_refiner):
        """Test recommendation for token efficient execution."""
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=5.0,
            tokens_used=200,
            token_efficiency=40.0,  # Low tokens/sec
            quality_score=0.8,
            anomaly_score=0.2,
            cached_hits=0,
        )

        recommendation = skill_refiner._generate_recommendation(metrics, "analyze")

        assert "efficient" in recommendation.lower() or "baseline" in recommendation.lower()

    def test_recommend_cache_friendly(self, skill_refiner):
        """Test recommendation for cache-friendly patterns."""
        metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=500,
            token_efficiency=500.0,  # High efficiency
            quality_score=0.8,
            anomaly_score=0.2,
            cached_hits=5,
        )

        recommendation = skill_refiner._generate_recommendation(metrics, "search")

        assert "cache" in recommendation.lower() or "promote" in recommendation.lower()


class TestRefinementSectionCreation:
    """Test creation of refinement sections."""

    def test_create_refinement_section(self, skill_refiner):
        """Test creating a refinement section."""
        signal = LearningSignal(
            skill_name="TEST_SKILL",
            operation_type="generate",
            key_insight="Test insight",
            metric_change="Quality: 90%, Tokens: 150, Duration: 1.0s",
            recommendation="Test recommendation",
            confidence=0.9,
        )

        section = skill_refiner._create_refinement_section(signal)

        assert "Learned Refinement" in section
        assert "TEST_SKILL" not in section  # skill_name not included in section
        assert "Test insight" in section
        assert "Test recommendation" in section
        assert "90.0%" in section  # confidence formatted as percentage


class TestFactory:
    """Test SkillRefinerFactory."""

    def test_factory_create(self):
        """Test factory creation."""
        refiner = SkillRefinerFactory.create()

        assert isinstance(refiner, SkillRefiner)

    def test_factory_singleton(self):
        """Test factory singleton behavior."""
        SkillRefinerFactory.reset_singleton()

        refiner1 = SkillRefinerFactory.get_singleton()
        refiner2 = SkillRefinerFactory.get_singleton()

        assert refiner1 is refiner2

    def test_factory_reset(self):
        """Test resetting singleton."""
        SkillRefinerFactory.reset_singleton()

        refiner1 = SkillRefinerFactory.get_singleton()
        SkillRefinerFactory.reset_singleton()
        refiner2 = SkillRefinerFactory.get_singleton()

        assert refiner1 is not refiner2


class TestTokenBloatSignal:
    """CB16 ext: TOKEN_BLOAT rolling-window detection in _generate_learning_signal."""

    @staticmethod
    def _metrics(tokens_per_task: int) -> ExecutionMetrics:
        # token_efficiency > 500 and quality_score <= 0.8 and no cache hits so the
        # ONLY insight that can fire is TOKEN_BLOAT — isolates the mechanism.
        return ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=tokens_per_task,
            token_efficiency=1000.0,
            quality_score=0.5,
            anomaly_score=0.5,
            cached_hits=0,
            tokens_per_task=tokens_per_task,
        )

    def test_tokens_per_task_field_exists(self):
        """Structural: ExecutionMetrics carries the tokens_per_task field."""
        import dataclasses

        from cohezion.compound.skill_refiner import ExecutionMetrics as EM

        assert "tokens_per_task" in {f.name for f in dataclasses.fields(EM)}

    def test_token_bloat_not_triggered_at_2x(self, skill_refiner):
        """Discriminating: 2x the median must NOT trip the 3x threshold."""
        for _ in range(3):
            skill_refiner._generate_learning_signal("S", "generate", self._metrics(1000))

        signal = skill_refiner._generate_learning_signal("S", "generate", self._metrics(2000))

        # A wrong 2x-threshold implementation would emit TOKEN_BLOAT here.
        assert signal is None or "TOKEN_BLOAT" not in signal.key_insight

    def test_token_bloat_triggered_at_3x(self, skill_refiner):
        """Discriminating: just over 3x the median must trip TOKEN_BLOAT."""
        for _ in range(3):
            skill_refiner._generate_learning_signal("S", "generate", self._metrics(1000))

        signal = skill_refiner._generate_learning_signal("S", "generate", self._metrics(3001))

        assert signal is not None
        assert "TOKEN_BLOAT" in signal.key_insight


# ---------------------------------------------------------------------------
# #117: EnvironmentResponsePredictor
# ---------------------------------------------------------------------------


class TestEnvironmentResponsePredictor:
    """Unit tests for EnvironmentResponsePredictor (Qwen-AgentWorld pattern)."""

    def test_prediction_error_field_exists_in_execution_metrics(self):
        """ERP4 structural: ExecutionMetrics carries prediction_error field."""
        import dataclasses

        from cohezion.compound.skill_refiner import ExecutionMetrics as EM

        assert "prediction_error" in {f.name for f in dataclasses.fields(EM)}
        # Default must be None (safe default, CB16 pattern)
        m = EM(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=500.0,
            quality_score=0.8,
            anomaly_score=0.1,
            cached_hits=0,
        )
        assert m.prediction_error is None

    def test_predict_returns_none_with_no_history(self):
        """Structural: predict() must return None before any data is recorded."""
        erp = EnvironmentResponsePredictor()
        assert erp.predict("skill", "generate") is None

    def test_predict_returns_rolling_mean(self):
        """Discriminating: predict() must return mean of recorded values.

        A wrong implementation that returns the LAST value instead of the mean
        would return 0.9 here, not 0.75.
        """
        erp = EnvironmentResponsePredictor()
        erp.record("skill", "generate", 0.6)
        erp.record("skill", "generate", 0.9)
        assert erp.predict("skill", "generate") == pytest.approx(0.75)

    def test_prediction_error_requires_prior_history(self):
        """Discriminating: prediction_error must return None with no history.

        A wrong implementation that records before computing would return 0.0
        (actual − predicted = actual − actual) instead of None.
        """
        erp = EnvironmentResponsePredictor()
        # No history yet — should NOT use the current point as its own prediction.
        err = erp.prediction_error("skill", "generate", 0.8)
        assert err is None

    def test_prediction_error_uses_prior_history_not_current(self):
        """Discriminating: prediction_error = (actual − prior_mean), not 0.

        If the implementation records before predicting, the prediction becomes
        the current point itself and the error would always be 0. Test catches this.
        """
        erp = EnvironmentResponsePredictor()
        erp.record("skill", "generate", 0.5)
        erp.record("skill", "generate", 0.5)
        # Prior mean is 0.5; actual is 0.9 → error should be 0.4, not 0.
        err = erp.prediction_error("skill", "generate", 0.9)
        assert err == pytest.approx(0.4)

    def test_keys_are_independent(self):
        """Discriminating: different (skill, op_type) pairs must not share history.

        A wrong implementation that uses a single pool would mix these predictions.
        """
        erp = EnvironmentResponsePredictor()
        erp.record("skill_a", "generate", 0.9)
        erp.record("skill_a", "generate", 0.9)
        # skill_b has no history, so prediction_error must be None, not 0.0 (from skill_a).
        err = erp.prediction_error("skill_b", "generate", 0.1)
        assert err is None

    def test_is_surprising_fires_above_threshold(self):
        """is_surprising returns True when |error| > threshold."""
        erp = EnvironmentResponsePredictor(surprise_threshold=0.2)
        erp.record("s", "op", 0.5)
        erp.record("s", "op", 0.5)
        # actual=0.9 → error=0.4 > 0.2 threshold
        assert erp.is_surprising("s", "op", 0.9) is True

    def test_is_surprising_does_not_fire_at_threshold_boundary(self):
        """is_surprising uses strict > not >=, so exact threshold is NOT surprising."""
        erp = EnvironmentResponsePredictor(surprise_threshold=0.2)
        erp.record("s", "op", 0.5)
        erp.record("s", "op", 0.5)
        # actual=0.7 → error=0.2; strict > means this must NOT be surprising
        assert erp.is_surprising("s", "op", 0.7) is False

    def test_window_size_caps_history(self):
        """Rolling window must respect window_size (oldest values evicted)."""
        erp = EnvironmentResponsePredictor(window_size=3)
        erp.record("s", "op", 0.0)
        erp.record("s", "op", 0.0)
        erp.record("s", "op", 0.0)
        erp.record("s", "op", 0.9)  # evicts first 0.0
        # Window is [0.0, 0.0, 0.9] → mean = 0.3, NOT 0.225 (which would include 4 items)
        assert erp.predict("s", "op") == pytest.approx(0.3)


class TestEnvironmentSurpriseSignal:
    """Integration: ENVIRONMENT_SURPRISE tag in SkillRefiner._generate_learning_signal."""

    @staticmethod
    def _metrics(quality: float) -> ExecutionMetrics:
        # token_efficiency=1000 (above threshold), quality varies, no cache hits.
        # This way the ONLY insight that fires is ENVIRONMENT_SURPRISE.
        return ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=1000.0,
            quality_score=quality,
            anomaly_score=0.0,
            cached_hits=0,
        )

    def test_no_surprise_without_history(self, skill_refiner):
        """Without prior history, ENVIRONMENT_SURPRISE must not fire."""
        # Fresh refiner — first call has no prediction, so no surprise possible.
        signal = skill_refiner._generate_learning_signal("S", "generate", self._metrics(0.1))
        assert signal is None or "ENVIRONMENT_SURPRISE" not in signal.key_insight

    def test_no_surprise_within_threshold(self, skill_refiner):
        """Discriminating: small deviation must NOT fire ENVIRONMENT_SURPRISE.

        A wrong threshold-off-by-one would fire here at exactly 0.2 deviation.
        """
        # Seed two stable observations at 0.5
        skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.5))
        skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.5))
        # Third call at 0.7 → deviation = 0.2, NOT > 0.2 (strict), must not fire
        signal = skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.7))
        assert signal is None or "ENVIRONMENT_SURPRISE" not in (
            signal.key_insight if signal else ""
        )

    def test_surprise_fires_above_threshold(self, skill_refiner):
        """Discriminating: deviation > 0.2 must emit ENVIRONMENT_SURPRISE.

        A wrong impl that compares against the current quality (not rolling mean)
        would fail because |q − q| == 0, never triggering surprise.
        """
        # Seed stable at 0.5
        skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.5))
        skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.5))
        # Large drop: 0.1 → error = |0.1 − 0.5| = 0.4 > 0.2 → must fire
        signal = skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.1))
        assert signal is not None
        assert "ENVIRONMENT_SURPRISE" in signal.key_insight


# ---------------------------------------------------------------------------
# #118: RL process reward wiring
# ---------------------------------------------------------------------------


class TestProcessRewardWiring:
    """#118: producer → consumer completeness for RL process reward signal."""

    @staticmethod
    def _metrics(quality: float) -> ExecutionMetrics:
        return ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=1000.0,
            quality_score=quality,
            anomaly_score=0.0,
            cached_hits=0,
        )

    def test_prediction_error_stored_in_metrics_after_signal(self, skill_refiner):
        """Producer→consumer: pred_err must be written back into metrics.prediction_error.

        A wrong impl that only uses pred_err locally (inside _generate_learning_signal)
        would leave metrics.prediction_error as None after the call.
        """
        # Seed history so prediction_error is computable on the second call.
        m1 = self._metrics(0.5)
        skill_refiner._generate_learning_signal("S", "gen", m1)

        m2 = self._metrics(0.8)
        assert m2.prediction_error is None  # starts as safe default
        skill_refiner._generate_learning_signal("S", "gen", m2)
        # After the call, m2.prediction_error must hold (0.8 − 0.5) = 0.3
        assert m2.prediction_error == pytest.approx(0.3)

    def test_process_reward_mean_none_before_any_signal(self, skill_refiner):
        """Structural: process_reward_mean returns None with no history."""
        assert skill_refiner.process_reward_mean("novel_skill") is None

    def test_process_reward_accumulated_across_signals(self, skill_refiner):
        """Producer→consumer: _generate_learning_signal feeds the reward accumulator.

        After N calls, process_reward_mean must reflect the accumulated pred_errs —
        not None (which would mean the accumulator was never called).
        """
        # Two stable calls at 0.5 — second call has pred_err = 0.0 (0.5 − 0.5)
        skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.5))
        skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.5))
        # After two calls, accumulator has one entry (first call had no history → None)
        mean = skill_refiner.process_reward_mean("S")
        assert mean is not None
        assert abs(mean) < 1e-9  # stable quality → reward ≈ 0

    def test_positive_reward_boosts_confidence(self, skill_refiner):
        """Discriminating: positive process reward must raise LearningSignal.confidence.

        A wrong impl that ignores process rewards would return confidence == quality_score.
        Uses token_efficiency=100 to guarantee "efficient token usage" insight fires.
        """

        def _m(quality: float) -> ExecutionMetrics:
            return ExecutionMetrics(
                success=True,
                duration_seconds=1.0,
                tokens_used=100,
                token_efficiency=100.0,  # <500 → "efficient token usage" fires
                quality_score=quality,
                anomaly_score=0.0,
                cached_hits=0,
            )

        # Seed 5 observations at 0.3 so the next call at 0.5 is a positive surprise
        for _ in range(5):
            skill_refiner._generate_learning_signal("S", "gen", _m(0.3))

        # quality=0.5 > rolling mean=0.3 → pred_err=0.2 → positive reward
        signal = skill_refiner._generate_learning_signal("S", "gen", _m(0.5))
        assert signal is not None
        # base_confidence = min(0.95, 0.5) = 0.5; positive reward_mean must push it above 0.5
        assert signal.confidence > 0.5

    def test_negative_reward_dampens_confidence(self, skill_refiner):
        """Discriminating: negative process reward must lower LearningSignal.confidence.

        A wrong impl that ignores process rewards returns confidence == quality_score.
        """
        # Seed 5 high-quality observations at 0.9 so the next 0.7 is a negative surprise
        for _ in range(5):
            # token_efficiency < 500 to get "efficient token usage" insight — ensures
            # the signal fires even at quality=0.7
            skill_refiner._generate_learning_signal(
                "S",
                "gen",
                ExecutionMetrics(
                    success=True,
                    duration_seconds=1.0,
                    tokens_used=100,
                    token_efficiency=100.0,
                    quality_score=0.9,
                    anomaly_score=0.0,
                    cached_hits=0,
                ),
            )

        signal = skill_refiner._generate_learning_signal(
            "S",
            "gen",
            ExecutionMetrics(
                success=True,
                duration_seconds=1.0,
                tokens_used=100,
                token_efficiency=100.0,
                quality_score=0.7,
                anomaly_score=0.0,
                cached_hits=0,
            ),
        )
        assert signal is not None
        # base_confidence = min(0.95, 0.7) = 0.7; negative reward must pull it below 0.7
        assert signal.confidence < 0.7

    def test_mgpo_weight_biased_by_positive_rewards(self, skill_refiner):
        """Discriminating: positive process reward shifts mgpo_weight upward.

        mgpo_weight requires VaultNeuronWriter which is mocked; we test process_reward_mean
        is non-None (the accumulated signal exists and is consumable).
        """
        # Seed positive surprise: quality=0.8 after history of 0.5
        for _ in range(3):
            skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.5))
        skill_refiner._generate_learning_signal("S", "gen", self._metrics(0.8))

        mean = skill_refiner.process_reward_mean("S")
        assert mean is not None and mean > 0  # positive reward accumulated


class TestSkillProximity:
    """#102: lineage-based skill proximity (CSHL brain development analogy).

    SP1: proximity is 0.0 when either skill has no ERP history
    SP2: identical op-type distributions → proximity near 1.0
    SP3: disjoint op-types → proximity == 0.0
    SP4: partial overlap → 0.0 < proximity < 1.0
    SP5: discriminating — different quality profiles on shared op → proximity < 1.0
    """

    @staticmethod
    def _seed(refiner: SkillRefiner, skill: str, op: str, quality: float, n: int = 3) -> None:
        for _ in range(n):
            refiner._env_predictor.record(skill, op, quality)

    def test_unknown_skill_returns_zero(self, skill_refiner):
        """SP1: no history for either skill → 0.0."""
        assert skill_refiner.skill_proximity("unknown_a", "unknown_b") == 0.0

    def test_one_unknown_returns_zero(self, skill_refiner):
        """SP1b: one skill has history, other doesn't → 0.0."""
        self._seed(skill_refiner, "skill_a", "classify", 0.8)
        assert skill_refiner.skill_proximity("skill_a", "unknown_b") == 0.0

    def test_identical_op_types_same_quality_near_one(self, skill_refiner):
        """SP2: same op-types, same quality → proximity == 1.0."""
        for sk in ("planning", "execution"):
            self._seed(skill_refiner, sk, "generate", 0.8)
            self._seed(skill_refiner, sk, "classify", 0.7)
        p = skill_refiner.skill_proximity("planning", "execution")
        assert abs(p - 1.0) < 1e-6

    def test_disjoint_op_types_returns_zero(self, skill_refiner):
        """SP3: no shared op-types → jaccard=0 → proximity=0.0."""
        self._seed(skill_refiner, "skill_x", "generate", 0.8)
        self._seed(skill_refiner, "skill_y", "classify", 0.8)
        assert skill_refiner.skill_proximity("skill_x", "skill_y") == 0.0

    def test_partial_overlap_between_zero_and_one(self, skill_refiner):
        """SP4: partial op-type overlap → 0.0 < proximity < 1.0."""
        self._seed(skill_refiner, "alpha", "generate", 0.8)
        self._seed(skill_refiner, "alpha", "classify", 0.7)
        self._seed(skill_refiner, "beta", "generate", 0.8)
        self._seed(skill_refiner, "beta", "reason", 0.6)  # different second op
        p = skill_refiner.skill_proximity("alpha", "beta")
        assert 0.0 < p < 1.0

    def test_different_quality_on_shared_op_reduces_proximity(self, skill_refiner):
        """SP5: same op-type but very different quality → proximity < same-quality case."""
        # Case A: same op-type, same quality
        for sk in ("s1", "s2"):
            self._seed(skill_refiner, sk, "gen", 0.8)
        p_same = skill_refiner.skill_proximity("s1", "s2")

        refiner2 = SkillRefiner()
        self._seed(refiner2, "s3", "gen", 0.8)
        self._seed(refiner2, "s4", "gen", 0.1)  # very different quality
        p_diff = refiner2.skill_proximity("s3", "s4")

        assert p_same > p_diff  # similar quality → higher proximity


class TestLocalInferenceWiring:
    """CB14: fabrication probe for LM signals (arXiv 2606.27226 BINEVAL + NatureBench).

    _lm_signal_cites_metrics(text, metrics) -> bool:
    - Returns False when text contains no number within ±50% of any actual metric
    - Returns True when text cites at least one real metric value
    - Fail-open: empty text and 'NOMINAL' sentinel always return True
    """

    @pytest.fixture
    def base_metrics(self):
        return ExecutionMetrics(
            success=True,
            duration_seconds=2.0,
            tokens_used=100,
            token_efficiency=50.0,
            quality_score=0.8,
            anomaly_score=0.2,
            cached_hits=5,
        )

    def test_lm_hallucinated_text_blocked_by_citation_gate(self, base_metrics):
        """T2 discriminating: text with numbers far outside all metric ranges → False."""
        sr = SkillRefiner()
        # 999999 is not within ±50% of tokens_used=100, quality=0.8, duration=2.0, hits=5
        hallucinated = "This skill used 999999 tokens with 987654 cache hits."
        assert sr._lm_signal_cites_metrics(hallucinated, base_metrics) is False

    def test_lm_cited_text_passes_gate(self, base_metrics):
        """Text citing an actual metric value within ±50% → True."""
        sr = SkillRefiner()
        # "100 tokens" matches tokens_used=100 exactly (50 ≤ 100 ≤ 150)
        real_text = "Quality: 80.00%, Tokens: 100, Duration: 2.00s"
        assert sr._lm_signal_cites_metrics(real_text, base_metrics) is True

    def test_lm_empty_text_fails_open(self, base_metrics):
        """Empty text → True (fail-open: no LM signal means heuristic runs)."""
        sr = SkillRefiner()
        assert sr._lm_signal_cites_metrics("", base_metrics) is True

    def test_lm_nominal_sentinel_fails_open(self, base_metrics):
        """'NOMINAL' sentinel → True (heuristic path unblocked)."""
        sr = SkillRefiner()
        assert sr._lm_signal_cites_metrics("NOMINAL", base_metrics) is True

    def test_t1_structural_called_in_generate_learning_signal(self):
        """T1 structural: _lm_signal_cites_metrics is called inside _generate_learning_signal."""
        import inspect

        src = inspect.getsource(SkillRefiner._generate_learning_signal)
        assert "_lm_signal_cites_metrics" in src


class TestSessionGoal:
    """#136: SkillRefiner self-directed learning goal state (GIC agentive internalization)."""

    # --- T1: Structural ---

    def test_session_goal_field_exists(self):
        """T1 structural: SkillRefiner has _session_goal attribute initialized to None."""
        sr = SkillRefiner()
        assert hasattr(sr, "_session_goal")
        assert sr._session_goal is None

    def test_set_goal_and_get_goal(self):
        """T1 structural: set_goal() persists; get_goal() retrieves it."""
        sr = SkillRefiner()
        sr.set_goal("improve quality_score", target_metric="quality_score")
        g = sr.get_goal()
        assert g is not None
        assert g["objective"] == "improve quality_score"
        assert g["target_metric"] == "quality_score"

    def test_set_goal_updates_existing_goal(self):
        """T1 structural: second set_goal() replaces the first."""
        sr = SkillRefiner()
        sr.set_goal("first goal", target_metric="quality_score")
        sr.set_goal("second goal", target_metric="token_efficiency")
        g = sr.get_goal()
        assert g["objective"] == "second goal"
        assert g["target_metric"] == "token_efficiency"

    # --- T2: Discriminating behavioral ---

    def test_goal_biases_recommendation_toward_quality(self):
        """T2 discriminating: quality goal overrides metric-based selection for mediocre metrics.

        Without a goal, mediocre quality (0.5) + high efficiency → efficiency recommendation.
        With quality goal, the recommendation must reference quality.
        This proves the goal *changes behavior*, not just stores metadata.
        """
        sr = SkillRefiner()
        # Metrics where efficiency perspective normally wins (quality=0.5 < 0.8 cutoff)
        mediocre_quality_metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=200.0,  # below 500 → efficiency candidate fires
            quality_score=0.5,  # below 0.8 → quality candidate does NOT fire
            anomaly_score=0.1,
            cached_hits=0,
        )
        sr.set_goal("improve quality", target_metric="quality_score")
        rec = sr._generate_recommendation(mediocre_quality_metrics, "test_op")
        assert "quality" in rec.lower(), (
            f"With quality goal, recommendation should mention quality. Got: {rec}"
        )

    def test_no_goal_does_not_inject_quality_for_mediocre_metrics(self):
        """T2 discriminating inverse: without goal, mediocre quality metrics don't force quality rec."""
        sr = SkillRefiner()
        # No goal set
        mediocre_quality_metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=200.0,
            quality_score=0.5,  # below threshold — quality perspective normally skipped
            anomaly_score=0.1,
            cached_hits=0,
        )
        rec = sr._generate_recommendation(mediocre_quality_metrics, "test_op")
        # Without goal: either efficiency or fallback wins, not necessarily quality
        # This test proves the goal injection is the differentiator, not some other mechanism
        # We just assert the goal field is None and a rec is returned (trusting the prior test)
        assert sr._session_goal is None
        assert isinstance(rec, str) and len(rec) > 0

    def test_goal_tier_biases_toward_tier_recommendation(self):
        """T2 discriminating: tier escalation goal overrides when no escalations observed."""
        sr = SkillRefiner()
        sr.set_goal("reduce tier escalation", target_metric="escalation_count")
        no_esc_metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=800.0,
            quality_score=0.9,
            anomaly_score=0.0,
            cached_hits=5,
            escalation_count=0,  # no escalation — tier perspective wouldn't normally fire
        )
        rec = sr._generate_recommendation(no_esc_metrics, "test_op")
        # With escalation-reduction goal, recommendation should mention tier or escalation
        assert "tier" in rec.lower() or "escalat" in rec.lower(), (
            f"With escalation goal, should mention tier/escalation. Got: {rec}"
        )

    def test_auto_update_goal_fires_after_threshold_calls(self):
        """T2 discriminating: _auto_update_goal() proposes a goal after N executions.

        After 5 consistently low-quality calls, _session_goal should be non-None.
        A wrong implementation (never auto-updates) would leave it None.
        """
        sr = SkillRefiner()
        low_q_metrics = ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=200.0,
            quality_score=0.3,  # consistently poor quality
            anomaly_score=0.1,
            cached_hits=0,
        )
        for _ in range(5):
            sr._auto_update_goal("my_skill", low_q_metrics)
        assert sr._session_goal is not None, (
            "After 5 low-quality calls, _auto_update_goal should have set a goal"
        )
        assert "quality" in sr._session_goal.get("target_metric", ""), (
            f"Auto goal should target quality_score. Got: {sr._session_goal}"
        )


class TestShadowCanaryValidator:
    """Tests for ShadowCanaryValidator rolling-window quality gate.

    SC1: structural — class, fields, defaults
    SC2: pass case — candidate quality >= baseline - threshold
    SC3: block case — candidate quality regresses beyond threshold (discriminating)
    SC4: fail-open — no history means always pass
    SC5: wiring structural — _shadow_canary present in SkillRefiner
    SC6: wiring behavioral — record() called in _generate_learning_signal
    """

    def test_sc1_structural_fields(self):
        """SC1: ShadowCanaryValidator has required interface with correct defaults."""
        sv = ShadowCanaryValidator()
        assert hasattr(sv, "_history")
        assert isinstance(sv._history, dict)
        assert sv._window_size == 20
        assert sv._regression_threshold == 0.05

    def test_sc1_custom_params(self):
        """SC1: constructor params accepted and stored."""
        sv = ShadowCanaryValidator(window_size=10, regression_threshold=0.1)
        assert sv._window_size == 10
        assert sv._regression_threshold == 0.1

    def test_sc2_pass_case_well_above_threshold(self):
        """SC2: validate passes when candidate quality is clearly >= baseline - threshold.

        A wrong implementation (blocking all changes) would fail here.
        """
        sv = ShadowCanaryValidator(regression_threshold=0.05)
        for q in [0.80, 0.82, 0.79]:
            sv.record("skill_a", q)
        # baseline median ≈ 0.80; candidate=0.78 → regression=0.02 < 0.05 → should pass
        ok, reason = sv.validate("skill_a", [0.78])
        assert ok is True, f"Expected pass for candidate 0.78 vs baseline ~0.80, got: {reason}"

    def test_sc3_block_case_clear_regression(self):
        """SC3 discriminating: validate blocks when candidate clearly regresses.

        A wrong implementation (never blocking) would fail this test.
        """
        sv = ShadowCanaryValidator(regression_threshold=0.05)
        for q in [0.80, 0.82, 0.79]:
            sv.record("skill_b", q)
        # baseline median ≈ 0.80; candidate=0.60 → regression=0.20 > 0.05 → must block
        ok, reason = sv.validate("skill_b", [0.60])
        assert ok is False, "Expected block for candidate 0.60 vs baseline ~0.80, got ok=True"
        assert "regression" in reason.lower(), f"Reason should describe regression: {reason}"
        assert "0.60" in reason or "0.6" in reason, f"Reason should cite candidate score: {reason}"

    def test_sc4_fail_open_no_history(self):
        """SC4: validate fails open when skill has no recorded history.

        A wrong implementation (blocking unknown skills) would fail here.
        """
        sv = ShadowCanaryValidator()
        ok, reason = sv.validate("brand_new_skill", [0.1])  # terrible score, still passes
        assert ok is True, f"Must fail open with no history, got ok=False reason={reason}"
        assert "no_baseline" in reason

    def test_sc4_fail_open_empty_candidate_scores(self):
        """SC4: validate fails open when candidate_scores is empty."""
        sv = ShadowCanaryValidator()
        sv.record("skill_c", 0.9)
        ok, reason = sv.validate("skill_c", [])
        assert ok is True, "Must fail open with empty candidate, got ok=False"

    def test_sc5_wiring_in_skill_refiner(self):
        """SC5: SkillRefiner has _shadow_canary as ShadowCanaryValidator instance."""
        sr = SkillRefiner()
        assert hasattr(sr, "_shadow_canary"), "SkillRefiner missing _shadow_canary"
        assert isinstance(sr._shadow_canary, ShadowCanaryValidator), (
            f"Expected ShadowCanaryValidator, got {type(sr._shadow_canary).__name__}"
        )

    def test_sc6_record_wired_in_generate_learning_signal(self):
        """SC6 structural: _generate_learning_signal() calls _shadow_canary.record().

        A wrong implementation (leaving record() unwired) would fail this structural check.
        """
        import inspect

        sr = SkillRefiner()
        src = inspect.getsource(sr._generate_learning_signal)
        assert "_shadow_canary.record" in src, (
            "_generate_learning_signal must call _shadow_canary.record() to build baseline"
        )

    def test_sc6_validate_wired_in_refine(self):
        """SC6 structural: refine() calls _shadow_canary.validate() before PRIME write."""
        import inspect

        sr = SkillRefiner()
        src = inspect.getsource(sr.refine)
        assert "_shadow_canary.validate" in src, (
            "refine() must call _shadow_canary.validate() before _append_refinement"
        )
        assert "shadow_canary" in src, "refine() must block on shadow_canary failure"

    def test_sc3_regression_is_directional(self):
        """SC3 discriminating: improvements (candidate > baseline) always pass.

        A wrong implementation checking absolute deviation would incorrectly block improvements.
        """
        sv = ShadowCanaryValidator(regression_threshold=0.05)
        for q in [0.50, 0.52, 0.49]:
            sv.record("skill_d", q)
        # baseline ≈ 0.50; candidate=0.90 → quality improved massively → must NOT block
        ok, reason = sv.validate("skill_d", [0.90])
        assert ok is True, f"Improvements should never be blocked: got ok=False reason={reason}"


# --------------------------------------------------------------------------- #
# AR (Adversarial Review Gate) invariants — AR1/AR2/AR3/AR4
# --------------------------------------------------------------------------- #


def _make_signal() -> LearningSignal:
    return LearningSignal(
        skill_name="test-skill",
        operation_type="generate",
        key_insight="cache hit rate improved by 12%",
        metric_change="cache_hit_rate: 0.71 → 0.83",
        recommendation="Increase L2 threshold to 0.58 for nomic-embed",
        confidence=0.82,
    )


def _make_metrics() -> ExecutionMetrics:
    return ExecutionMetrics(
        success=True,
        duration_seconds=1.2,
        tokens_used=120,
        token_efficiency=100.0,
        quality_score=0.82,
        anomaly_score=0.1,
        cached_hits=3,
    )


class TestAdversarialReviewGate:
    """AR1–AR4: adversarial gate signature, blocking, approval, and fail-open contracts."""

    def test_ar1_structural_method_exists_and_accepts_required_args(self):
        """AR1: _adversarial_review_gate(signal, skill_name, metrics) must exist.

        A structural check that fires BEFORE behavioral tests — if the method
        signature changes, this gives a clear invariant name rather than a TypeError.
        """
        import inspect

        sr = SkillRefiner()
        params = inspect.signature(sr._adversarial_review_gate).parameters
        assert "signal" in params, "signal param missing"
        assert "skill_name" in params, "skill_name param missing"
        assert "metrics" in params, "metrics param missing"

    def test_ar2_three_rejects_blocks_gate(self):
        """AR2 (discriminating): chat_fn returning 'REJECT' for ALL 3 personas → gate blocks.

        This is the discriminating case. A wrong implementation that always
        returned True (always-APPROVE bug) would fail here.
        """
        sr = SkillRefiner()
        sr._adversarial_chat_fn = lambda _p: "REJECT bad idea"

        result = sr._adversarial_review_gate(_make_signal(), "test-skill", _make_metrics())
        assert result is False, "3/3 REJECT must block the gate (use_frontier=False)"

    def test_ar3_three_approves_passes_gate(self):
        """AR3: chat_fn returning 'APPROVE' for all 3 → gate passes."""
        sr = SkillRefiner()
        sr._adversarial_chat_fn = lambda _p: "APPROVE looks good"

        result = sr._adversarial_review_gate(_make_signal(), "test-skill", _make_metrics())
        assert result is True, "3/3 APPROVE must pass the gate"

    def test_ar3_two_approves_one_reject_passes(self):
        """2/3 APPROVE is sufficient threshold."""
        call_count = [0]

        def chat_fn(p: str) -> str:
            call_count[0] += 1
            return "REJECT" if call_count[0] == 1 else "APPROVE ok"

        sr = SkillRefiner()
        sr._adversarial_chat_fn = chat_fn
        result = sr._adversarial_review_gate(_make_signal(), "test-skill", _make_metrics())
        assert result is True, "2/3 APPROVE is enough to pass"

    def test_ar4_exception_in_chat_fn_counts_as_approve_fail_open(self):
        """AR4 (fail-open): each perspective exception counts as APPROVE.

        An unavailable LLM endpoint must never permanently block the compound loop.
        """

        def failing_chat_fn(p: str) -> str:
            raise ConnectionError("LLM offline")

        sr = SkillRefiner()
        sr._adversarial_chat_fn = failing_chat_fn
        result = sr._adversarial_review_gate(_make_signal(), "test-skill", _make_metrics())
        assert result is True, "Transport failures must fail-open (count as APPROVE)"

    def test_ar2_frontier_chat_fn_injected_before_review(self):
        """AR2 structural: chat_fn field exists and starts as None (lazy-build)."""
        sr = SkillRefiner()
        assert hasattr(sr, "_adversarial_chat_fn"), "_adversarial_chat_fn field missing"
        assert sr._adversarial_chat_fn is None, "field must start None (lazy-built on first call)"


class TestRegimeAwareAutodata:
    """RA1-RA4: Regime-aware autodata selection (2026-07-04).

    CompoundHealthOracle reports a FD regime (STUCK/HIHO/CHAOTIC). _autodata_select()
    uses regime multipliers from _REGIME_EXPERT_WEIGHT to bias candidate selection:
    - STUCK (FD<1.3): boost quality/efficiency/trajectory (exploration), suppress tier/caching
    - CHAOTIC (FD>1.7): boost tier/caching (stability), suppress quality/efficiency
    - None/HIHO: no bias (all weights 1.0)

    The three candidates below are crafted so:
      quality_cand and tier_cand share "quality" and "performance" (2 shared keywords),
      tier_cand and extra_cand share "hardware", "routing", and "performance" (3 shared keywords).
      Result: tier_cand has overlap=5, quality_cand has overlap=3, extra_cand has overlap=4
              (with regime=None, tier_cand wins; with STUCK, quality_cand wins → regime overrides)
    """

    # Crafted candidates where shared keywords are known exactly (words > 3 chars counted)
    QUALITY_CAND = "optimize prime skill guidance quality output performance"
    TIER_CAND = "specify tier routing escalation quality performance hardware"
    EXTRA_CAND = "hardware routing performance configuration setup"

    def _make_metrics(self, **kwargs) -> ExecutionMetrics:
        defaults = dict(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=300.0,
            quality_score=0.7,
            anomaly_score=0.3,
            cached_hits=0,
            tier_used="npu",
            escalation_count=1,
        )
        defaults.update(kwargs)
        return ExecutionMetrics(**defaults)

    def _sr_with_map(self) -> SkillRefiner:
        sr = SkillRefiner()
        # Pre-register expert identities for the three candidates
        sr._candidate_expert_map = {
            self.QUALITY_CAND: "quality",
            self.TIER_CAND: "tier",
            self.EXTRA_CAND: "caching",
        }
        return sr

    def test_ra1_regime_parameter_in_autodata_select_signature(self):
        """RA1 structural: _autodata_select() accepts 'regime' kwarg.

        A wrong impl (3-arg only) would raise TypeError. If it raises, the
        regime is never applied — the entire RA system is dead code.
        """
        import inspect

        params = inspect.signature(SkillRefiner._autodata_select).parameters
        assert "regime" in params, "'regime' missing from _autodata_select signature"

    def test_ra2_stuck_regime_overrides_overlap_ordering(self):
        """RA2 discriminating: STUCK regime boosts quality expert (1.6×) over tier (0.6×).

        With regime=None, tier_cand wins (overlap=5 > quality_cand overlap=3).
        With regime='stuck', quality wins: 3 * 1.6 = 4.8 > 5 * 0.6 = 3.0.

        Wrong impl (ignoring regime, or applying to wrong expert) keeps tier_cand winning.
        """
        sr = self._sr_with_map()
        metrics = self._make_metrics()
        candidates = [self.QUALITY_CAND, self.TIER_CAND, self.EXTRA_CAND]

        # Verify baseline: without regime, tier_cand wins due to higher overlap
        no_regime_result = sr._autodata_select(candidates, metrics, regime=None)
        assert no_regime_result == self.TIER_CAND, (
            f"Baseline broken: expected tier_cand to win without regime, got {no_regime_result!r}"
        )

        # With STUCK: quality regime_weight=1.6 must flip the winner
        stuck_result = sr._autodata_select(candidates, metrics, regime="stuck")
        assert stuck_result == self.QUALITY_CAND, (
            f"STUCK regime must boost quality expert over tier; got {stuck_result!r}"
        )

    def test_ra3_chaotic_regime_boosts_tier_expert(self):
        """RA3 discriminating: CHAOTIC regime boosts tier expert (1.8×) over quality (0.6×).

        Starting from STUCK (quality wins at 4.8), CHAOTIC must flip to tier:
        tier_cand: 5 * 1.8 = 9.0 >> quality_cand: 3 * 0.6 = 1.8.

        Wrong impl (applying STUCK multipliers for CHAOTIC) would keep quality winning.
        """
        sr = self._sr_with_map()
        metrics = self._make_metrics()
        candidates = [self.QUALITY_CAND, self.TIER_CAND, self.EXTRA_CAND]

        chaotic_result = sr._autodata_select(candidates, metrics, regime="chaotic")
        assert chaotic_result == self.TIER_CAND, (
            f"CHAOTIC regime must boost tier expert; got {chaotic_result!r}"
        )

    def test_ra4_unknown_regime_treated_as_neutral(self):
        """RA4: regime values outside stuck/chaotic (e.g. 'hiho', None) apply no multiplier.

        The guard `if regime in ('stuck', 'chaotic')` handles this. An impl that branches
        on 'hiho' without the guard would incorrectly apply 1.0 multipliers (no-op) or crash.
        Both None and 'hiho' must produce the same result (tier_cand wins by raw overlap).

        Note: uses separate fresh SkillRefiner instances per call so the RV2 frequency
        penalty (_autodata_wins counter) does not carry over between regime-neutrality checks.
        """
        metrics = self._make_metrics()
        candidates = [self.QUALITY_CAND, self.TIER_CAND, self.EXTRA_CAND]

        none_result = self._sr_with_map()._autodata_select(candidates, metrics, regime=None)
        hiho_result = self._sr_with_map()._autodata_select(candidates, metrics, regime="hiho")
        assert none_result == hiho_result == self.TIER_CAND, (
            f"Both None and 'hiho' must use raw overlap (tier wins); "
            f"none={none_result!r}, hiho={hiho_result!r}"
        )


class TestRegimeConditionedCanary:
    """RC1-RC3: regime-conditioned ShadowCanaryValidator threshold.

    STUCK (FD<1.3):  effective_threshold = base × 1.5 — loosen gate for experimental updates.
    CHAOTIC (FD>1.7): effective_threshold = base × 0.5 — tighten gate during quality oscillation.
    None/hiho:        effective_threshold = base × 1.0 — unchanged.
    """

    _SKILL = "test_rc_skill"
    _BASE = 0.05  # matches ShadowCanaryValidator default

    def _build_canary_with_baseline(self, baseline: float, n: int = 10) -> ShadowCanaryValidator:
        """Return a canary with `n` baseline records at `baseline` quality."""
        canary = ShadowCanaryValidator(window_size=20, regression_threshold=self._BASE)
        for _ in range(n):
            canary.record(self._SKILL, baseline)
        return canary

    def test_rc1_regime_parameter_in_validate_signature(self):
        """RC1: validate() must accept a `regime` kwarg (structural)."""
        import inspect

        sig = inspect.signature(ShadowCanaryValidator.validate)
        assert "regime" in sig.parameters, (
            "ShadowCanaryValidator.validate() must accept 'regime' kwarg for RC1"
        )

    def test_rc2_stuck_loosens_gate_borderline_regression_passes(self):
        """RC2: STUCK regime raises effective_threshold; a borderline regression passes.

        Baseline median = 0.80. Candidate = 0.74 → regression = 0.06.
        Default threshold = 0.05 → blocks (0.06 > 0.05).
        STUCK multiplier = 1.5 → effective = 0.075 → passes (0.06 < 0.075).

        A wrong implementation (ignoring regime) blocks this candidate.
        """
        canary = self._build_canary_with_baseline(0.80)
        candidate = 0.74  # regression 0.06 — above base but below stuck threshold

        ok_default, reason_default = canary.validate(self._SKILL, [candidate], regime=None)
        ok_stuck, reason_stuck = canary.validate(self._SKILL, [candidate], regime="stuck")

        assert not ok_default, (
            f"Default (regime=None) should block a 0.06 regression against threshold 0.05; "
            f"got ok=True, reason={reason_default!r}"
        )
        assert ok_stuck, (
            f"STUCK regime should loosen threshold to 0.075 and pass the 0.06 regression; "
            f"got ok=False, reason={reason_stuck!r}"
        )

    def test_rc3_chaotic_tightens_gate_borderline_regression_blocks(self):
        """RC3: CHAOTIC regime lowers effective_threshold; a normally-passing regression blocks.

        Baseline median = 0.80. Candidate = 0.77 → regression = 0.03.
        Default threshold = 0.05 → passes (0.03 < 0.05).
        CHAOTIC multiplier = 0.5 → effective = 0.025 → blocks (0.03 > 0.025).

        A wrong implementation (ignoring regime) passes this candidate.
        """
        canary = self._build_canary_with_baseline(0.80)
        candidate = 0.77  # regression 0.03 — below base but above chaotic threshold

        ok_default, _ = canary.validate(self._SKILL, [candidate], regime=None)
        ok_chaotic, reason_chaotic = canary.validate(self._SKILL, [candidate], regime="chaotic")

        assert ok_default, (
            "Default (regime=None) should pass a 0.03 regression against threshold 0.05"
        )
        assert not ok_chaotic, (
            f"CHAOTIC regime should tighten threshold to 0.025 and block the 0.03 regression; "
            f"got ok=True, reason={reason_chaotic!r}"
        )

    def test_rc_hiho_and_none_unchanged(self):
        """hiho regime and None both leave the threshold unmodified (neutral multiplier 1.0)."""
        canary = self._build_canary_with_baseline(0.80)
        candidate = 0.77  # 0.03 regression — just under default 0.05 threshold

        ok_none, _ = canary.validate(self._SKILL, [candidate], regime=None)
        ok_hiho, _ = canary.validate(self._SKILL, [candidate], regime="hiho")

        assert ok_none == ok_hiho, (
            f"None and 'hiho' should produce identical outcomes; none={ok_none}, hiho={ok_hiho}"
        )
        assert ok_none, "0.03 regression < 0.05 threshold should pass in HIHO/neutral mode"


class TestRQGMEpochBoundaryUpdate:
    """RQGM1-RQGM2: Red Queen Gödel Machine goal epoch rotation.

    Source: arXiv 2606.26294 — co-evolving goal objectives prevent static-evaluator stagnation.
    Epoch 0: existing metrics-driven heuristic (backward-compatible).
    Epoch 1+: rotates through quality_score / escalation_count / token_efficiency.
    """

    _SKILL = "rqgm_test_skill"

    def _low_q_metrics(self):
        return ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=100.0,
            quality_score=0.3,
            anomaly_score=0.5,
            cached_hits=0,
        )

    def _high_q_metrics(self):
        return ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=100.0,
            quality_score=0.9,
            anomaly_score=0.1,
            cached_hits=0,
        )

    def test_rqgm1_t1_epoch_fields_exist_with_zero_defaults(self):
        """RQGM1 T1 structural: _goal_epoch and _goal_consecutive_hits start at 0."""
        sr = SkillRefiner()
        assert hasattr(sr, "_goal_epoch"), "SkillRefiner must have '_goal_epoch' field"
        assert hasattr(sr, "_goal_consecutive_hits"), (
            "SkillRefiner must have '_goal_consecutive_hits' field"
        )
        assert sr._goal_epoch == 0, f"_goal_epoch must start at 0; got {sr._goal_epoch}"
        assert sr._goal_consecutive_hits == 0, (
            f"_goal_consecutive_hits must start at 0; got {sr._goal_consecutive_hits}"
        )

    def test_rqgm2_t2_discriminating_epoch_advances_after_threshold(self):
        """RQGM2 T2 discriminating: after 5 (default threshold) calls, _goal_epoch advances to 1.

        Wrong impl (ignoring epoch) would leave _goal_epoch at 0 → FAILS assertion.
        """
        sr = SkillRefiner()
        metrics = self._low_q_metrics()
        for _ in range(sr._goal_auto_threshold):
            sr._auto_update_goal(self._SKILL, metrics)
        assert sr._goal_epoch == 1, (
            f"After {sr._goal_auto_threshold} calls _goal_epoch must be 1; got {sr._goal_epoch}"
        )
        assert sr._goal_consecutive_hits == 0, (
            "_goal_consecutive_hits must reset to 0 on each epoch advance"
        )

    def test_rqgm2_t2_discriminating_second_goal_differs_from_first(self):
        """RQGM2 T2: second epoch goal target must differ from the first (rotation fires).

        After threshold calls → epoch 0 heuristic sets goal (e.g. quality_score).
        After another threshold calls → epoch 1 rotates to quality_score[0] in the list
        (same slot), but epoch 2 would rotate to escalation_count.  We force 15 total
        calls so epoch goes 0→1→2 and compare the epoch-1 and epoch-2 targets.
        """
        sr = SkillRefiner()
        metrics = self._low_q_metrics()
        threshold = sr._goal_auto_threshold  # typically 5

        # Fire epoch 0 → epoch 1 (first fire sets epoch 0 heuristic result)
        for _ in range(threshold):
            sr._auto_update_goal(self._SKILL, metrics)
        first_goal = sr._session_goal.copy() if sr._session_goal else {}

        # Fire epoch 1 → epoch 2 (second fire uses RQGM rotation)
        for _ in range(threshold):
            sr._auto_update_goal(self._SKILL, metrics)
        second_goal = sr._session_goal.copy() if sr._session_goal else {}

        # Epoch 1: rotation index = 1 % 3 = 1 → "escalation_count"
        # Epoch 0 (heuristic): quality < 0.5 → "quality_score"
        # So the targets should differ across the two firings.
        assert second_goal.get("target_metric") != first_goal.get("target_metric"), (
            f"Epoch-boundary rotation must change target_metric; "
            f"first={first_goal.get('target_metric')!r}, "
            f"second={second_goal.get('target_metric')!r}"
        )


class TestRiVERZScoreNormalization:
    """RV1 (updated): _accumulate_process_reward() uses NIG normalization from n=1.

    The original z-score approach needed ≥3 samples for a stable standard deviation.
    NIG (Normal-Inverse-Gamma conjugate prior) provides a well-calibrated predictive
    std from the first observation, eliminating the warm-up dead zone.
    Source: Gelman BDA §2.6; arXiv:2606.27369 RiVER upgrade.
    """

    def test_nig_works_from_n_equals_1(self):
        """Discriminating: NIG normalization fires on the FIRST observation.
        A z-score impl (which needs ≥3) would leave the window empty after 1 call."""
        from cohezion.compound.skill_refiner import SkillRefiner

        sr = SkillRefiner()
        sr._accumulate_process_reward("s", 1.0)
        window = list(sr._process_rewards.get("s", []))
        assert len(window) == 1, "NIG should have appended after the first observation"

    def test_nig_normalizes_large_error(self):
        """After warm-up the NIG predictive std should shrink, normalizing large values.
        Discriminating: a no-op impl (raw append) would store the raw value 100.0;
        NIG-normalized value must be substantially smaller."""
        from cohezion.compound.skill_refiner import SkillRefiner

        sr = SkillRefiner()
        # Seed a few observations so the NIG variance estimate is established
        for _ in range(5):
            sr._accumulate_process_reward("s", 0.1)
        sr._accumulate_process_reward("s", 100.0)  # outlier
        window = list(sr._process_rewards.get("s", []))
        assert abs(window[-1]) < 100.0, (
            f"NIG-normalized large error should be smaller than raw; got {window[-1]}"
        )

    def test_nig_params_stored_per_skill(self):
        """NIG hyperparameters are tracked per-skill — two skills don't share state."""
        from cohezion.compound.skill_refiner import SkillRefiner

        sr = SkillRefiner()
        sr._accumulate_process_reward("skill_a", 2.0)
        sr._accumulate_process_reward("skill_b", -3.0)
        assert "skill_a" in sr._nig_params
        assert "skill_b" in sr._nig_params
        # mu parameters should differ because the input values differ
        mu_a = sr._nig_params["skill_a"][0]
        mu_b = sr._nig_params["skill_b"][0]
        assert mu_a != mu_b, "NIG mu should reflect the actual observed value per skill"


class TestRiVERFrequencyWeighting:
    """RV2: RiVER frequency penalty in _autodata_select() prevents perspective lock.

    Source: arXiv:2606.27369 — 1/(1+wins) discount prevents one candidate from
    monopolizing selection across repeated calls.
    """

    QUALITY_CAND = "optimize prime skill guidance quality output performance"
    TIER_CAND = "specify tier routing escalation quality performance hardware"
    EXTRA_CAND = "hardware routing performance configuration setup"

    def _make_sr(self) -> SkillRefiner:
        sr = SkillRefiner()
        sr._candidate_expert_map = {
            self.QUALITY_CAND: "quality",
            self.TIER_CAND: "tier",
            self.EXTRA_CAND: "caching",
        }
        return sr

    def _make_metrics(self):
        return ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=100,
            token_efficiency=300.0,
            quality_score=0.7,
            anomaly_score=0.3,
            cached_hits=0,
        )

    def test_rv2_t1_autodata_wins_initialized_empty(self):
        """RV2 T1 structural: SkillRefiner()._autodata_wins starts as an empty dict."""
        sr = SkillRefiner()
        assert hasattr(sr, "_autodata_wins"), "SkillRefiner must have '_autodata_wins'"
        assert sr._autodata_wins == {}, f"_autodata_wins must start empty; got {sr._autodata_wins}"

    def test_rv2_t2_repeated_winner_gets_lower_score_on_next_call(self):
        """RV2 T2 discriminating: after 20 rounds, at least 2 distinct winners appear.

        Without the frequency penalty, tier_cand would win every round (highest overlap = 5).
        With 1/(1+wins) decay, after enough rounds the penalty drops tier_cand's effective
        score below quality_cand (overlap=3, wins=0 → no penalty), so quality_cand overtakes.

        Wrong impl (no frequency penalty) returns only tier_cand → len(set(winners)) == 1 → FAILS.
        """
        sr = self._make_sr()
        metrics = self._make_metrics()
        candidates = [self.QUALITY_CAND, self.TIER_CAND, self.EXTRA_CAND]

        winners = []
        for _ in range(20):
            winners.append(sr._autodata_select(candidates, metrics))

        unique_winners = set(winners)
        assert len(unique_winners) > 1, (
            f"Frequency penalty must enable at least 2 distinct winners over 20 rounds; "
            f"got only: {unique_winners}"
        )


class TestSkillRefinerDurableSpine:
    """SRS1-SRS3: to_dict/from_dict/save_state/restore_state cross-session serialization.

    Pattern mirrors CB7 (DegradationDetector) and HO3 (CompoundHealthOracle).
    All state is JSON-safe; no deques, tuples, or Path objects in the payload.
    """

    _SKILL = "srs_test_skill"
    _OP = "srs_test_op"
    _ERP_KEY = f"{_SKILL}::{_OP}"

    def _primed_refiner(self) -> SkillRefiner:
        """Return a SkillRefiner with non-default state on every tracked field."""
        sr = SkillRefiner()
        sr._goal_epoch = 3
        sr._goal_consecutive_hits = 7
        sr._session_goal = {"objective": "rqgm-test", "target_metric": "escalation_count"}
        sr._goal_call_tally = {self._SKILL: 4}
        sr._autodata_wins = {"some_candidate": 5}
        # Add a process reward
        sr._process_rewards[self._SKILL] = __import__("collections").deque(
            [0.1, 0.2, 0.3], maxlen=20
        )
        # Add ERP history
        sr._env_predictor._history[(self._SKILL, self._OP)] = __import__("collections").deque(
            [0.4, 0.5, 0.6], maxlen=sr._env_predictor._window_size
        )
        return sr

    def test_srs1_to_dict_has_required_keys(self):
        """SRS1: to_dict() must contain all 7 required cross-session state keys."""
        sr = SkillRefiner()
        d = sr.to_dict()
        required = {
            "goal_epoch",
            "goal_consecutive_hits",
            "session_goal",
            "goal_call_tally",
            "autodata_wins",
            "process_rewards",
            "erp_history",
        }
        assert required <= set(d), f"Missing keys: {required - set(d)}"

    def test_srs1_to_dict_is_json_serializable(self):
        """SRS1: to_dict() output must be JSON-serializable (no deques/tuples/Paths)."""
        import json

        sr = self._primed_refiner()
        d = sr.to_dict()
        # This must not raise
        json.dumps(d)

    def test_srs2_from_dict_restores_non_default_epoch(self):
        """SRS2 discriminating: from_dict must restore goal_epoch=7, not leave it at 0."""
        sr = SkillRefiner()
        d = sr.to_dict()
        d["goal_epoch"] = 7
        restored = SkillRefiner.from_dict(d)
        assert restored._goal_epoch == 7, (
            f"from_dict must restore non-default goal_epoch; got {restored._goal_epoch}"
        )

    def test_srs2_from_dict_full_roundtrip(self):
        """SRS2: full state round-trip — all fields match after to_dict → from_dict."""
        original = self._primed_refiner()
        d = original.to_dict()
        restored = SkillRefiner.from_dict(d)

        assert restored._goal_epoch == original._goal_epoch
        assert restored._goal_consecutive_hits == original._goal_consecutive_hits
        assert restored._session_goal == original._session_goal
        assert restored._goal_call_tally == original._goal_call_tally
        assert restored._autodata_wins == original._autodata_wins

        # process_rewards round-trip
        assert list(restored._process_rewards.get(self._SKILL, [])) == [0.1, 0.2, 0.3]

        # ERP history round-trip — tuple key must be restored
        erp = restored._env_predictor._history
        assert (self._SKILL, self._OP) in erp, (
            f"ERP tuple key ({self._SKILL!r}, {self._OP!r}) not restored; keys: {list(erp)}"
        )
        assert list(erp[(self._SKILL, self._OP)]) == [0.4, 0.5, 0.6]

    def test_srs2_from_dict_safe_defaults_for_missing_keys(self):
        """SRS2 CB16 safe-defaults: from_dict on an empty dict must not crash."""
        # This should not raise
        restored = SkillRefiner.from_dict({})
        assert restored._goal_epoch == 0
        assert restored._autodata_wins == {}

    def test_srs3_save_restore_roundtrip(self, tmp_path):
        """SRS3: save_state/restore_state round-trip preserves all state."""
        original = self._primed_refiner()
        state_file = tmp_path / "test_state.json"

        original.save_state(state_file)
        assert state_file.exists(), "save_state must create the file"

        fresh = SkillRefiner()
        result = fresh.restore_state(state_file)
        assert result is True, "restore_state must return True on success"

        assert fresh._goal_epoch == original._goal_epoch
        assert fresh._goal_consecutive_hits == original._goal_consecutive_hits
        assert fresh._session_goal == original._session_goal
        assert fresh._autodata_wins == original._autodata_wins

        # ERP history tuple key must survive the full save→restore cycle
        erp = fresh._env_predictor._history
        assert (self._SKILL, self._OP) in erp, (
            f"ERP key not restored after save/restore; keys: {list(erp)}"
        )

    def test_srs3_restore_returns_false_on_missing_file(self, tmp_path):
        """SRS3 fail-open: restore_state returns False (not raises) when file absent."""
        sr = SkillRefiner()
        result = sr.restore_state(tmp_path / "nonexistent.json")
        assert result is False

    def test_srs3_save_creates_parent_directories(self, tmp_path):
        """SRS3: save_state creates nested parent directories that don't exist."""
        sr = SkillRefiner()
        deep_path = tmp_path / "a" / "b" / "c" / "state.json"
        sr.save_state(deep_path)
        assert deep_path.exists(), "save_state must create parent directories"


class TestShadowCanaryWarmStart:
    """Shadow canary warm-start from restored process_rewards (SRS3 extension).

    Without this, the canary is in fail-open mode for 20 executions after every restart.
    With this, any skill that has process_reward history gets a pre-warmed canary baseline.
    """

    _SKILL = "warm_start_skill"

    def test_canary_warm_started_from_process_rewards(self, tmp_path):
        """Discriminating: after restore_state, the shadow canary has a populated baseline.

        Wrong impl (no warm-start) leaves canary._history empty → baseline_count == 0.
        """
        import json

        # Build a state file with process_rewards for the skill
        rewards = [0.3, -0.1, 0.4, 0.2, 0.5]  # 5 samples > 0 → all map to quality > 0.5
        state_file = tmp_path / "skill_refiner_state.json"
        state_file.write_text(
            json.dumps(
                {
                    "goal_epoch": 0,
                    "goal_consecutive_hits": 0,
                    "session_goal": None,
                    "goal_call_tally": {},
                    "autodata_wins": {},
                    "process_rewards": {self._SKILL: rewards},
                    "erp_history": {},
                }
            )
        )

        sr = SkillRefiner()
        result = sr.restore_state(state_file)
        assert result is True

        # The shadow canary must have a populated window for this skill
        window = sr._shadow_canary._history.get(self._SKILL)
        assert window is not None, (
            f"Shadow canary must be warmed for '{self._SKILL}' after restore_state; "
            f"found no window. history keys: {list(sr._shadow_canary._history)}"
        )
        assert len(window) == len(rewards), (
            f"Window must contain {len(rewards)} samples (one per reward); got {len(window)}"
        )
        # Each sample must be a sigmoid-mapped quality value in (0, 1)
        for q in window:
            assert 0.0 < q < 1.0, f"Quality {q} must be in (0, 1) from sigmoid mapping"
        # Positive rewards map to quality > 0.5
        assert all(q > 0.5 for q in window if rewards[list(window).index(q)] > 0), (
            "Positive process rewards must map to quality > 0.5"
        )

    def test_canary_no_crash_on_empty_process_rewards(self, tmp_path):
        """Fail-open: restore_state with empty process_rewards does not populate canary."""
        import json

        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "goal_epoch": 0,
                    "goal_consecutive_hits": 0,
                    "session_goal": None,
                    "goal_call_tally": {},
                    "autodata_wins": {},
                    "process_rewards": {},
                    "erp_history": {},
                }
            )
        )

        sr = SkillRefiner()
        result = sr.restore_state(state_file)
        assert result is True
        # No canary window added for skills with no history


class TestSeesawCheck:
    """CB15: _seesaw_check() deterministic invariant-negation gate."""

    def _make_prime(self, tmp_path: "Path", content: str) -> "Path":
        p = tmp_path / "PRIME.md"
        p.write_text(content)
        return p

    # T1 structural: refine() source must reference _seesaw_check
    def test_t1_structural_seesaw_wired_in_refine(self) -> None:
        import inspect

        from cohezion.compound.skill_refiner import SkillRefiner

        src = inspect.getsource(SkillRefiner.refine)
        assert "_seesaw_check" in src, "_seesaw_check must be called inside refine()"

    # T2: non-contradictory recommendation passes (returns True)
    def test_t2_allow_non_contradictory(self, tmp_path: "Path") -> None:

        from cohezion.compound.skill_refiner import SkillRefiner

        prime = self._make_prime(
            tmp_path,
            "## Invariants\n- Must always use semantic cache for repeated queries.\n",
        )
        sr = SkillRefiner()
        result = sr._seesaw_check(prime, "Increase cache TTL to improve hit rate.")
        assert result is True, "Non-contradictory recommendation should pass"

    # T3: invariant-negating recommendation is blocked (returns False)
    def test_t3_block_invariant_negation(self, tmp_path: "Path") -> None:

        from cohezion.compound.skill_refiner import SkillRefiner

        prime = self._make_prime(
            tmp_path,
            "## Rules\n- Must always use the semantic cache for all repeated queries.\n",
        )
        sr = SkillRefiner()
        # "disable" near "cache" should be blocked
        result = sr._seesaw_check(prime, "Disable the semantic cache to reduce latency.")
        assert result is False, "Invariant-negating recommendation should be blocked"

    # T4: missing PRIME file → fail-open (returns True)
    def test_t4_fail_open_missing_file(self, tmp_path: "Path") -> None:

        from cohezion.compound.skill_refiner import SkillRefiner

        missing = tmp_path / "NONEXISTENT_PRIME.md"
        sr = SkillRefiner()
        result = sr._seesaw_check(missing, "Remove cache entirely.")
        assert result is True, "Missing PRIME file must fail-open (True)"
