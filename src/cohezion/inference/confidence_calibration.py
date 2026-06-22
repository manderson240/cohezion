"""Platt-scaling calibration for RouteDecision.confidence.

Raw classifier confidence values (e.g. 0.82, 0.85) are rule-authored heuristics,
not calibrated probabilities. This module wraps task_classifier.classify() with
a Platt calibration layer so that ``calibrated_classify(prompt).confidence``
tracks empirical accuracy.

Platt scaling: f_cal = σ(A * f_raw + B), where σ is the logistic sigmoid.
Default parameters: A=1.0, B=0.0 → identity (no-op until fit with real data).

Ref: Platt (1999), "Probabilistic outputs for support vector machines..."
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cohezion.inference.task_classifier import RouteDecision, classify


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class PlattCalibrator:
    """Logistic calibration for scalar confidence scores.

    Usage::
        cal = PlattCalibrator()
        cal.fit([0.82, 0.75, 0.90, 0.70], [1, 0, 1, 1])
        p = cal.calibrate(0.82)  # calibrated probability
    """

    A: float = 1.0
    B: float = 0.0
    _fitted: bool = field(default=False, init=False, repr=False)

    def fit(self, raw_scores: list[float], labels: list[int]) -> PlattCalibrator:
        """Fit A and B via simple gradient descent on log-loss.

        Parameters
        ----------
        raw_scores:
            Raw confidence scores from classify().confidence.
        labels:
            1 = classifier was correct, 0 = incorrect.
        """
        if len(raw_scores) != len(labels):
            raise ValueError("raw_scores and labels must have equal length")
        if not raw_scores:
            return self

        # Gradient descent on binary cross-entropy loss
        a, b = self.A, self.B
        lr = 0.1
        for _ in range(200):
            da = db = 0.0
            for f, y in zip(raw_scores, labels):
                p = _sigmoid(a * f + b)
                err = p - y
                da += err * f
                db += err
            n = len(raw_scores)
            a -= lr * da / n
            b -= lr * db / n

        self.A = a
        self.B = b
        self._fitted = True
        return self

    def calibrate(self, raw_score: float) -> float:
        """Return calibrated probability for a raw confidence score."""
        return _sigmoid(self.A * raw_score + self.B)

    @property
    def fitted(self) -> bool:
        return self._fitted


# Module-level default calibrator — identity until fit() is called
_default_calibrator: PlattCalibrator = PlattCalibrator()


def set_default_calibrator(cal: PlattCalibrator) -> None:
    """Replace the module-level calibrator (e.g. after fitting on empirical data)."""
    global _default_calibrator
    _default_calibrator = cal


def calibrated_classify(prompt: str) -> RouteDecision:
    """Classify prompt and return RouteDecision with calibrated confidence.

    Wraps task_classifier.classify() and replaces raw .confidence with
    the Platt-calibrated value. Routing decision (node, output_type,
    quality_gate_chars) is unchanged — only .confidence is adjusted.

    Falls back to raw confidence on any calibration error.
    """
    decision = classify(prompt)
    try:
        cal_conf = _default_calibrator.calibrate(decision.confidence)
        return RouteDecision(
            node=decision.node,
            output_type=decision.output_type,
            quality_gate_chars=decision.quality_gate_chars,
            confidence=round(cal_conf, 4),
            reason=decision.reason
            + f" [platt A={_default_calibrator.A:.3f} B={_default_calibrator.B:.3f}]",
            preferred_model=decision.preferred_model,
        )
    except Exception:
        return decision
