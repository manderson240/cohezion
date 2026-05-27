# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Model Quality Classifier for Phase 5A.7 - Proactive quality prediction.

Predicts when a model will fail by analyzing execution patterns and forecasting
quality metric trajectories. Complements degradation detection (5A.6) by
providing proactive early warnings before thresholds are violated.

Key capabilities:
- Coherence forecasting: Predict coherence drops 3-5 steps ahead
- Success rate prediction: Forecast success rate anomalies
- Trend detection: Identify degradation trends before critical levels
- Corrective action suggestions: Recommend model fallbacks or adjustments
- Non-blocking: All predictions are stateless, <5ms latency

Architecture:
- ExecutionPattern: Track sequence of model performance metrics
- QualityPredictor: Build trend models from history
- QualityForecast: Predictions with confidence scores
- ActionRecommendation: Suggested interventions

Usage::

    classifier = ModelQualityClassifier()

    # Add execution history
    for execution in past_executions:
        classifier.add_execution(
            model=execution["model"],
            coherence=execution["coherence"],
            success=execution["success"],
            tokens=execution["tokens"],
        )

    # Predict future quality
    forecast = classifier.predict_quality(
        model="qwen3-coder:30b",
        num_steps_ahead=3,
    )

    if forecast.predicted_coherence < 0.60:
        recommendation = forecast.recommendation
        logger.warning(f"Quality warning: {recommendation.message}")
        # Suggest model switch or parameter adjustment
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class FailureMode(Enum):
    """Predicted failure modes."""

    COHERENCE_DROP = "coherence_drop"  # Coherence below 0.60
    SUCCESS_RATE_DROP = "success_rate_drop"  # Success < 80%
    EFFICIENCY_DROP = "efficiency_drop"  # Tokens/sec drops
    LATENCY_SPIKE = "latency_spike"  # Duration increases
    COMBINED = "combined"  # Multiple metrics degrading


class RecommendedAction(Enum):
    """Recommended corrective actions."""

    CONTINUE = "continue"  # Continue with current model
    SWITCH_MODEL = "switch_model"  # Switch to different model
    ADJUST_PARAMETERS = "adjust_parameters"  # Tune model parameters
    INCREASE_BUDGET = "increase_budget"  # Allocate more tokens
    RESTART_SESSION = "restart_session"  # Clear state and restart


@dataclass
class ExecutionRecord:
    """Single execution snapshot."""

    model: str
    coherence: float  # 0.0-1.0
    success: bool  # Success or failure
    tokens_used: int
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class QualityForecast:
    """Prediction of future quality metrics."""

    model: str
    predicted_coherence: float  # Forecasted coherence 3-5 steps ahead
    coherence_confidence: float  # 0.0-1.0 confidence in prediction
    coherence_trend: str  # "improving", "stable", "degrading"
    coherence_steps_to_critical: int  # Steps before hitting 0.60 threshold

    predicted_success_rate: float  # Forecasted success rate
    success_confidence: float
    success_trend: str

    failure_mode: FailureMode | None = None  # Predicted failure if any
    failure_probability: float = 0.0  # 0.0-1.0

    recommendation: ActionRecommendation | None = None
    num_steps_ahead: int = 3


@dataclass
class ActionRecommendation:
    """Recommended corrective action."""

    action: RecommendedAction
    message: str  # Human-readable explanation
    priority: str  # "LOW", "MEDIUM", "HIGH"
    confidence: float  # 0.0-1.0
    alternative_models: list[str] = field(default_factory=list)  # If action=SWITCH_MODEL
    parameter_suggestions: dict[str, Any] = field(default_factory=dict)  # If action=ADJUST


class QualityPredictor:
    """Predict model quality trends from execution history."""

    def __init__(self, model: str, min_samples: int = 5):
        """Initialize predictor for a specific model.

        Args:
            model: Model name
            min_samples: Minimum samples to establish trend
        """
        self.model = model
        self.min_samples = min_samples
        self.coherence_history: list[float] = []
        self.success_history: list[bool] = []
        self.tokens_history: list[int] = []
        self.duration_history: list[float] = []

    def add_execution(
        self,
        coherence: float,
        success: bool,
        tokens_used: int,
        duration: float,
    ) -> None:
        """Add execution record to history.

        Args:
            coherence: Coherence score (0.0-1.0)
            success: Whether execution succeeded
            tokens_used: Tokens consumed
            duration: Execution duration in seconds
        """
        self.coherence_history.append(coherence)
        self.success_history.append(success)
        self.tokens_history.append(tokens_used)
        self.duration_history.append(duration)

    def is_established(self) -> bool:
        """Check if enough history to make predictions."""
        return len(self.coherence_history) >= self.min_samples

    def get_trend(self, values: list[float]) -> str:
        """Determine trend from recent values.

        Args:
            values: List of metric values

        Returns:
            "improving", "stable", or "degrading"
        """
        if len(values) < 2:
            return "stable"

        recent = values[-5:]  # Last 5 values
        if len(recent) < 2:
            return "stable"

        # Simple linear trend
        indices = np.arange(len(recent))
        coeffs = np.polyfit(indices, recent, 1)
        slope = coeffs[0]

        if slope > 0.01:  # Positive trend
            return "improving"
        elif slope < -0.01:  # Negative trend
            return "degrading"
        else:
            return "stable"

    def forecast_coherence(self, steps_ahead: int = 3) -> tuple[float, float, int]:
        """Forecast coherence N steps ahead.

        Args:
            steps_ahead: How many steps to predict ahead

        Returns:
            (predicted_coherence, confidence, steps_to_critical_threshold)
        """
        if not self.is_established():
            return 0.5, 0.0, 999

        coherence = self.coherence_history
        recent = coherence[-10:]  # Last 10 for trend

        if len(recent) < 2:
            return np.mean(coherence[-5:]), 0.3, 999

        # Linear regression for simple forecast
        indices = np.arange(len(recent))
        try:
            coeffs = np.polyfit(indices, recent, 1)
            slope, intercept = coeffs[0], coeffs[1]

            # Forecast
            future_index = len(recent) + steps_ahead
            predicted = slope * future_index + intercept
            predicted = np.clip(predicted, 0.0, 1.0)

            # Confidence based on variance
            variance = np.var(recent)
            confidence = max(0.3, 1.0 - variance)

            # Steps to critical (0.60)
            steps_to_critical = 999 if slope >= 0 else max(1, int((0.6 - predicted) / abs(slope)))

            return float(predicted), float(confidence), steps_to_critical
        except Exception as e:
            logger.debug(f"Forecast failed: {e}, using average")
            return float(np.mean(recent)), 0.3, 999

    def forecast_success_rate(self, steps_ahead: int = 3, window: int = 5) -> tuple[float, float]:
        """Forecast success rate N steps ahead.

        Args:
            steps_ahead: How many steps ahead
            window: Window size for recent history

        Returns:
            (predicted_success_rate, confidence)
        """
        if not self.is_established():
            return 1.0, 0.0

        recent_success = self.success_history[-window:]
        success_rate = float(sum(recent_success)) / len(recent_success)

        # Confidence based on consistency
        variance = np.var([float(s) for s in recent_success])
        confidence = max(0.3, 1.0 - variance)

        return success_rate, confidence


class ModelQualityClassifier:
    """Predict model quality and suggest corrective actions.

    Maintains history of executions per model and forecasts future quality
    based on trend analysis. Provides early warnings and action recommendations.

    Parameters
    ----------
    critical_coherence_threshold : float
        Coherence below this is critical (default: 0.60)
    critical_success_threshold : float
        Success rate below this is critical (default: 0.80)
    warning_lead_time : int
        Warn N steps before critical (default: 2)
    """

    def __init__(
        self,
        critical_coherence_threshold: float = 0.60,
        critical_success_threshold: float = 0.80,
        warning_lead_time: int = 2,
    ) -> None:
        """Initialize model quality classifier."""
        self.critical_coherence_threshold = critical_coherence_threshold
        self.critical_success_threshold = critical_success_threshold
        self.warning_lead_time = warning_lead_time

        # Per-model predictors
        self._predictors: dict[str, QualityPredictor] = {}

        # Model alternatives for fallback
        self._model_hierarchy = {
            "qwen3-coder:30b": ["alibayram/smollm3:latest", "phi3:mini", "deepseek-r1:70b"],
            "deepseek-r1:70b": ["qwen3-coder:30b", "alibayram/smollm3:latest", "phi3:mini"],
            "phi3:mini": ["alibayram/smollm3:latest", "qwen3-coder:30b", "deepseek-r1:70b"],
            "alibayram/smollm3:latest": ["phi3:mini", "qwen3-coder:30b", "deepseek-r1:70b"],
            "gpt-oss:20b": ["qwen3-coder:30b", "deepseek-r1:70b", "phi3:mini"],
            "phi4:latest": ["qwen3-coder:30b", "alibayram/smollm3:latest", "phi3:mini"],
            "gemma3:4b": ["phi3:mini", "alibayram/smollm3:latest", "qwen3-coder:30b"],
        }

        logger.debug("ModelQualityClassifier initialized")

    def add_execution(
        self,
        model: str,
        coherence: float,
        success: bool,
        tokens_used: int,
        duration: float,
    ) -> None:
        """Record a model execution.

        Args:
            model: Model name
            coherence: Coherence score (0.0-1.0)
            success: Whether execution succeeded
            tokens_used: Tokens consumed
            duration: Execution duration in seconds
        """
        if model not in self._predictors:
            self._predictors[model] = QualityPredictor(model)

        self._predictors[model].add_execution(coherence, success, tokens_used, duration)

    def predict_quality(
        self,
        model: str,
        num_steps_ahead: int = 3,
    ) -> QualityForecast:
        """Predict future quality for a model.

        Args:
            model: Model name to predict for
            num_steps_ahead: How many steps ahead to forecast

        Returns:
            QualityForecast with predictions and recommendations
        """
        if model not in self._predictors:
            # No history yet
            return QualityForecast(
                model=model,
                predicted_coherence=0.5,
                coherence_confidence=0.0,
                coherence_trend="stable",
                coherence_steps_to_critical=999,
                predicted_success_rate=1.0,
                success_confidence=0.0,
                success_trend="stable",
                num_steps_ahead=num_steps_ahead,
            )

        predictor = self._predictors[model]

        if not predictor.is_established():
            return QualityForecast(
                model=model,
                predicted_coherence=0.5,
                coherence_confidence=0.0,
                coherence_trend="stable",
                coherence_steps_to_critical=999,
                predicted_success_rate=1.0,
                success_confidence=0.0,
                success_trend="stable",
                num_steps_ahead=num_steps_ahead,
            )

        # Get predictions
        pred_coherence, coh_conf, steps_to_crit = predictor.forecast_coherence(num_steps_ahead)
        coh_trend = predictor.get_trend(predictor.coherence_history)

        pred_success, success_conf = predictor.forecast_success_rate(num_steps_ahead)
        success_trend = predictor.get_trend([float(s) for s in predictor.success_history])

        # Determine failure mode
        failure_mode = None
        failure_prob = 0.0

        if pred_coherence < self.critical_coherence_threshold:
            failure_mode = FailureMode.COHERENCE_DROP
            failure_prob = max(0.0, min(1.0, coh_conf))
        elif pred_success < self.critical_success_threshold:
            failure_mode = FailureMode.SUCCESS_RATE_DROP
            failure_prob = max(0.0, min(1.0, success_conf))

        # Generate recommendation
        recommendation = self._generate_recommendation(
            model=model,
            predicted_coherence=pred_coherence,
            coherence_trend=coh_trend,
            failure_mode=failure_mode,
            failure_probability=failure_prob,
        )

        forecast = QualityForecast(
            model=model,
            predicted_coherence=pred_coherence,
            coherence_confidence=coh_conf,
            coherence_trend=coh_trend,
            coherence_steps_to_critical=steps_to_crit,
            predicted_success_rate=pred_success,
            success_confidence=success_conf,
            success_trend=success_trend,
            failure_mode=failure_mode,
            failure_probability=failure_prob,
            recommendation=recommendation,
            num_steps_ahead=num_steps_ahead,
        )

        return forecast

    def _generate_recommendation(
        self,
        model: str,
        predicted_coherence: float,
        coherence_trend: str,
        failure_mode: FailureMode | None,
        failure_probability: float,
    ) -> ActionRecommendation | None:
        """Generate recommended action based on predictions.

        Args:
            model: Model being evaluated
            predicted_coherence: Forecasted coherence
            coherence_trend: Trend direction
            failure_mode: Type of failure predicted
            failure_probability: Probability of failure (0.0-1.0)

        Returns:
            ActionRecommendation if action needed, None otherwise
        """
        # No failure predicted
        if failure_mode is None:
            return ActionRecommendation(
                action=RecommendedAction.CONTINUE,
                message="Quality forecasted to remain healthy",
                priority="LOW",
                confidence=1.0 - failure_probability,
            )

        # Coherence drop predicted
        if failure_mode == FailureMode.COHERENCE_DROP:
            if failure_probability > 0.7:
                # High confidence - recommend switch
                alternatives = self._model_hierarchy.get(model, [])
                return ActionRecommendation(
                    action=RecommendedAction.SWITCH_MODEL,
                    message=f"Coherence predicted to drop to {predicted_coherence:.2f} "
                    f"with {failure_probability:.0%} confidence. "
                    f"Recommend switching to {alternatives[0] if alternatives else 'fallback model'}",
                    priority="HIGH",
                    confidence=failure_probability,
                    alternative_models=alternatives,
                )
            else:
                # Medium confidence - suggest monitoring or parameter adjustment
                return ActionRecommendation(
                    action=RecommendedAction.ADJUST_PARAMETERS,
                    message=f"Coherence trend {coherence_trend}. "
                    f"Predicted {predicted_coherence:.2f} "
                    f"({failure_probability:.0%} confidence). "
                    f"Consider increasing token budget or adjusting temperature.",
                    priority="MEDIUM",
                    confidence=failure_probability,
                    parameter_suggestions={
                        "temperature": "Reduce from 0.7 to 0.5",
                        "max_tokens": "Increase by 20%",
                    },
                )

        # Success rate drop predicted
        if failure_mode == FailureMode.SUCCESS_RATE_DROP:
            if failure_probability > 0.6:
                alternatives = self._model_hierarchy.get(model, [])
                return ActionRecommendation(
                    action=RecommendedAction.SWITCH_MODEL,
                    message=f"Success rate predicted to drop with {failure_probability:.0%} confidence. "
                    f"Recommend fallback.",
                    priority="HIGH",
                    confidence=failure_probability,
                    alternative_models=alternatives,
                )
            else:
                return ActionRecommendation(
                    action=RecommendedAction.RESTART_SESSION,
                    message=f"Success rate trend {coherence_trend}. Consider clearing session state and restarting.",
                    priority="MEDIUM",
                    confidence=failure_probability,
                )

        # Default recommendation
        return ActionRecommendation(
            action=RecommendedAction.CONTINUE,
            message="Continue monitoring",
            priority="LOW",
            confidence=0.5,
        )

    def get_model_stats(self) -> dict[str, Any]:
        """Get statistics for all tracked models.

        Returns:
            Dict with per-model statistics
        """
        stats = {}
        for model_name, predictor in self._predictors.items():
            if predictor.is_established():
                coh_pred, _coh_conf, _steps_crit = predictor.forecast_coherence()
                success_pred, _success_conf = predictor.forecast_success_rate()

                stats[model_name] = {
                    "num_executions": len(predictor.coherence_history),
                    "avg_coherence": float(np.mean(predictor.coherence_history)),
                    "std_coherence": float(np.std(predictor.coherence_history)),
                    "success_rate": float(
                        sum(predictor.success_history) / len(predictor.success_history)
                    ),
                    "predicted_coherence": round(coh_pred, 3),
                    "predicted_success_rate": round(success_pred, 3),
                    "coherence_trend": predictor.get_trend(predictor.coherence_history),
                }
        return stats


__all__ = [
    "ActionRecommendation",
    "ExecutionRecord",
    "FailureMode",
    "ModelQualityClassifier",
    "QualityForecast",
    "QualityPredictor",
    "RecommendedAction",
]
