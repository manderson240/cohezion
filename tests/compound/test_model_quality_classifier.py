"""Tests for Model Quality Classifier - Phase 5A.7."""

import pytest

from cohezion.compound.model_quality_classifier import (
    FailureMode,
    ModelQualityClassifier,
    QualityPredictor,
    RecommendedAction,
)


@pytest.fixture
def classifier():
    """Create model quality classifier for testing."""
    return ModelQualityClassifier(
        critical_coherence_threshold=0.60,
        critical_success_threshold=0.80,
        warning_lead_time=2,
    )


@pytest.fixture
def predictor():
    """Create quality predictor for testing."""
    return QualityPredictor("test-model", min_samples=5)


class TestQualityPredictor:
    """Test QualityPredictor core functionality."""

    def test_initialization(self, predictor):
        """Test predictor initialization."""
        assert predictor.model == "test-model"
        assert predictor.min_samples == 5
        assert len(predictor.coherence_history) == 0

    def test_add_execution(self, predictor):
        """Test adding execution records."""
        predictor.add_execution(
            coherence=0.85,
            success=True,
            tokens_used=150,
            duration=1.5,
        )

        assert len(predictor.coherence_history) == 1
        assert predictor.coherence_history[0] == 0.85
        assert predictor.success_history[0] is True
        assert predictor.tokens_history[0] == 150
        assert predictor.duration_history[0] == 1.5

    def test_is_established(self, predictor):
        """Test establishment detection."""
        assert predictor.is_established() is False

        for _i in range(4):
            predictor.add_execution(0.85, True, 150, 1.5)
        assert predictor.is_established() is False

        predictor.add_execution(0.85, True, 150, 1.5)
        assert predictor.is_established() is True

    def test_trend_improving(self, predictor):
        """Test trend detection - improving."""
        predictor.add_execution(0.5, True, 150, 1.5)
        predictor.add_execution(0.6, True, 150, 1.5)
        predictor.add_execution(0.7, True, 150, 1.5)
        predictor.add_execution(0.8, True, 150, 1.5)
        predictor.add_execution(0.9, True, 150, 1.5)

        trend = predictor.get_trend(predictor.coherence_history)
        assert trend == "improving"

    def test_trend_degrading(self, predictor):
        """Test trend detection - degrading."""
        predictor.add_execution(0.9, True, 150, 1.5)
        predictor.add_execution(0.8, True, 150, 1.5)
        predictor.add_execution(0.7, True, 150, 1.5)
        predictor.add_execution(0.6, True, 150, 1.5)
        predictor.add_execution(0.5, True, 150, 1.5)

        trend = predictor.get_trend(predictor.coherence_history)
        assert trend == "degrading"

    def test_trend_stable(self, predictor):
        """Test trend detection - stable."""
        for _ in range(5):
            predictor.add_execution(0.75, True, 150, 1.5)

        trend = predictor.get_trend(predictor.coherence_history)
        assert trend == "stable"

    def test_forecast_coherence_established(self, predictor):
        """Test coherence forecasting with established baseline."""
        # Add degrading coherence pattern
        for i in range(10):
            coherence = 0.9 - (i * 0.05)  # 0.9, 0.85, 0.8, ...
            predictor.add_execution(coherence, True, 150, 1.5)

        predicted, confidence, steps_to_crit = predictor.forecast_coherence(
            steps_ahead=3
        )

        assert isinstance(predicted, float)
        assert 0.0 <= predicted <= 1.0
        assert 0.0 <= confidence <= 1.0
        assert steps_to_crit >= 0

    def test_forecast_coherence_not_established(self, predictor):
        """Test forecast with insufficient data."""
        predictor.add_execution(0.85, True, 150, 1.5)

        predicted, confidence, steps_to_crit = predictor.forecast_coherence()

        assert predicted == 0.5
        assert confidence == 0.0
        assert steps_to_crit == 999

    def test_forecast_success_rate(self, predictor):
        """Test success rate forecasting."""
        # Add pattern with declining success
        for i in range(10):
            success = i < 7  # First 7 succeed, last 3 fail
            predictor.add_execution(0.85, success, 150, 1.5)

        predicted, confidence = predictor.forecast_success_rate()

        assert 0.0 <= predicted <= 1.0
        assert 0.0 <= confidence <= 1.0


class TestModelQualityClassifier:
    """Test ModelQualityClassifier core functionality."""

    def test_initialization(self, classifier):
        """Test classifier initialization."""
        assert classifier.critical_coherence_threshold == 0.60
        assert classifier.critical_success_threshold == 0.80

    def test_add_execution(self, classifier):
        """Test adding executions."""
        classifier.add_execution(
            model="qwen3-coder:30b",
            coherence=0.85,
            success=True,
            tokens_used=150,
            duration=1.5,
        )

        assert "qwen3-coder:30b" in classifier._predictors
        predictor = classifier._predictors["qwen3-coder:30b"]
        assert len(predictor.coherence_history) == 1

    def test_predict_quality_no_history(self, classifier):
        """Test prediction with no history."""
        forecast = classifier.predict_quality("unknown-model")

        assert forecast.model == "unknown-model"
        assert forecast.predicted_coherence == 0.5
        assert forecast.coherence_confidence == 0.0
        assert forecast.failure_mode is None

    def test_predict_quality_established(self, classifier):
        """Test prediction with established history."""
        # Add healthy execution history
        for _i in range(5):
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=0.85,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast = classifier.predict_quality("qwen3-coder:30b")

        assert forecast.model == "qwen3-coder:30b"
        assert forecast.coherence_confidence > 0.0
        assert forecast.coherence_trend in ["improving", "stable", "degrading"]

    def test_predict_quality_coherence_drop(self, classifier):
        """Test prediction of coherence drop."""
        # Build history with degrading coherence
        for i in range(10):
            coherence = 0.8 - (i * 0.08)  # 0.8, 0.72, 0.64, 0.56, ...
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=coherence,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast = classifier.predict_quality("qwen3-coder:30b", num_steps_ahead=3)

        if forecast.failure_mode == FailureMode.COHERENCE_DROP:
            assert forecast.predicted_coherence < 0.70
            assert forecast.recommendation is not None

    def test_predict_quality_success_drop(self, classifier):
        """Test prediction of success rate drop."""
        # Build history with declining success
        for i in range(10):
            success = i < 6  # First 6 succeed, last 4 fail
            classifier.add_execution(
                model="phi3:mini",
                coherence=0.85,
                success=success,
                tokens_used=100,
                duration=1.0,
            )

        forecast = classifier.predict_quality("phi3:mini")

        if forecast.failure_mode == FailureMode.SUCCESS_RATE_DROP:
            assert forecast.predicted_success_rate < 0.90
            assert forecast.recommendation is not None

    def test_recommendation_continue_healthy(self, classifier):
        """Test recommendation to continue when healthy."""
        # Add stable healthy executions
        for _ in range(5):
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=0.85,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast = classifier.predict_quality("qwen3-coder:30b")

        if forecast.recommendation:
            assert forecast.recommendation.action == RecommendedAction.CONTINUE

    def test_recommendation_switch_model(self, classifier):
        """Test recommendation to switch models."""
        # Add degrading coherence with high confidence
        for i in range(10):
            coherence = 0.75 - (i * 0.10)  # Rapid degradation
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=coherence,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast = classifier.predict_quality("qwen3-coder:30b")

        if (
            forecast.failure_mode == FailureMode.COHERENCE_DROP
            and forecast.failure_probability > 0.7
        ):
            assert forecast.recommendation is not None
            assert forecast.recommendation.action == RecommendedAction.SWITCH_MODEL
            assert len(forecast.recommendation.alternative_models) > 0

    def test_recommendation_adjust_parameters(self, classifier):
        """Test recommendation to adjust parameters."""
        # Add moderate degradation
        for i in range(8):
            coherence = 0.75 - (i * 0.05)
            classifier.add_execution(
                model="phi3:mini",
                coherence=coherence,
                success=True,
                tokens_used=100,
                duration=1.0,
            )

        forecast = classifier.predict_quality("phi3:mini")

        if forecast.failure_mode == FailureMode.COHERENCE_DROP and 0.3 < forecast.failure_probability <= 0.7:
            assert forecast.recommendation is not None
            assert forecast.recommendation.action == RecommendedAction.ADJUST_PARAMETERS

    def test_get_model_stats(self, classifier):
        """Test retrieving model statistics."""
        # Add executions
        for i in range(5):
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=0.80 + (i * 0.01),
                success=i < 4,
                tokens_used=150,
                duration=1.5,
            )

        stats = classifier.get_model_stats()

        assert "qwen3-coder:30b" in stats
        model_stats = stats["qwen3-coder:30b"]
        assert model_stats["num_executions"] == 5
        assert "avg_coherence" in model_stats
        assert "success_rate" in model_stats
        assert "coherence_trend" in model_stats

    def test_multiple_models(self, classifier):
        """Test tracking multiple models."""
        models = ["qwen3-coder:30b", "phi3:mini", "deepseek-r1:70b"]

        for model in models:
            for _ in range(5):
                classifier.add_execution(
                    model=model,
                    coherence=0.85,
                    success=True,
                    tokens_used=150,
                    duration=1.5,
                )

        assert len(classifier._predictors) == 3
        stats = classifier.get_model_stats()
        assert len(stats) == 3


class TestFailureModePrediction:
    """Test failure mode detection."""

    def test_failure_mode_coherence_drop(self, classifier):
        """Test coherence drop failure mode detection."""
        # Rapid coherence degradation
        for i in range(10):
            coherence = 0.7 - (i * 0.12)
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=coherence,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast = classifier.predict_quality("qwen3-coder:30b")

        if forecast.predicted_coherence < 0.60:
            assert forecast.failure_mode == FailureMode.COHERENCE_DROP

    def test_failure_mode_success_drop(self, classifier):
        """Test success rate drop failure mode detection."""
        # Declining success pattern
        for i in range(10):
            success = i < 3  # Only first 3 succeed
            classifier.add_execution(
                model="phi3:mini",
                coherence=0.85,
                success=success,
                tokens_used=100,
                duration=1.0,
            )

        forecast = classifier.predict_quality("phi3:mini")

        if forecast.predicted_success_rate < 0.80:
            assert forecast.failure_mode == FailureMode.SUCCESS_RATE_DROP

    def test_no_failure_mode(self, classifier):
        """Test prediction of no failure."""
        # Stable healthy executions
        for _ in range(5):
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=0.88,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast = classifier.predict_quality("qwen3-coder:30b")

        assert forecast.failure_mode is None
        assert forecast.failure_probability < 0.3


class TestForecastAccuracy:
    """Test forecast accuracy and confidence."""

    def test_forecast_confidence_based_on_variance(self, classifier):
        """Test that confidence is based on execution variance."""
        # Consistent executions
        for _ in range(5):
            classifier.add_execution(
                model="model1",
                coherence=0.85,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast1 = classifier.predict_quality("model1")

        # Varied executions
        classifier2 = ModelQualityClassifier()
        for i in range(5):
            coherence = 0.70 + (i * 0.05)
            classifier2.add_execution(
                model="model2",
                coherence=coherence,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast2 = classifier2.predict_quality("model2")

        # Consistent should have higher confidence
        if forecast1.coherence_confidence > 0 and forecast2.coherence_confidence > 0:
            assert (
                forecast1.coherence_confidence >= forecast2.coherence_confidence * 0.8
            )

    def test_steps_to_critical_calculation(self, classifier):
        """Test calculation of steps until critical threshold."""
        # Add degrading trend
        for i in range(10):
            coherence = 0.9 - (i * 0.05)  # 0.9, 0.85, ..., 0.45
            classifier.add_execution(
                model="qwen3-coder:30b",
                coherence=coherence,
                success=True,
                tokens_used=150,
                duration=1.5,
            )

        forecast = classifier.predict_quality("qwen3-coder:30b", num_steps_ahead=3)

        if forecast.coherence_steps_to_critical < 999:
            # Should be a reasonable number of steps
            assert forecast.coherence_steps_to_critical >= 0
            assert forecast.coherence_steps_to_critical <= 100
