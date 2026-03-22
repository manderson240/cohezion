"""Tests for skill refiner learning from execution results."""

import pytest

from cohezion.compound.skill_refiner import (
    ExecutionMetrics,
    LearningSignal,
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

    def test_extract_metrics_calculates_token_efficiency(self, skill_refiner, sample_execution_result):
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

        assert "prioritize" in recommendation.lower()

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

        assert (
            "efficient" in recommendation.lower()
            or "baseline" in recommendation.lower()
        )

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
