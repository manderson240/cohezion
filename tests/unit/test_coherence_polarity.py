"""Coherence polarity regression (2026-07-10, markov-trace root cause).

The InflectionDetector's ``score`` is HEALTH polarity (1.0 healthy, penalized
down). Inverting it froze ``metrics["coherence"]`` at 0.385 on every healthy
cycle — zero information for all downstream health metrics. These tests pin:
(1) coherence RESPONDS to detector-score variation, (2) in the RIGHT direction
(healthier detector score -> higher coherence).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from cohezion.compound.executor import CompoundExecutor


def _run_with_detector_score(score: float) -> float:
    ex = CompoundExecutor(MagicMock(), enable_guardrails=False)
    ex.inflection_detector = MagicMock()
    ex.inflection_detector.detect_anomaly.return_value = SimpleNamespace(
        severity=SimpleNamespace(value="info"),
        score=score,
        issues=[],
        recommendations=[],
    )
    result = ex.execute_task(
        task_description="polarity regression task",
        skill_name="polarity-test",
        operation_type="generate",
        execute_fn=lambda g: ("output", {"quality_score": 0.8}),
    )
    assert result.success
    return float(result.metrics["coherence"])


def test_coherence_varies_with_detector_score():
    healthy = _run_with_detector_score(1.0)
    degraded = _run_with_detector_score(0.3)
    assert healthy != degraded, "coherence is frozen — detector score ignored"


def test_coherence_polarity_healthy_beats_degraded():
    healthy = _run_with_detector_score(1.0)
    degraded = _run_with_detector_score(0.3)
    assert healthy > degraded, (
        f"polarity inverted: healthy={healthy} <= degraded={degraded} "
        "(detector score is HEALTH, must feed coherence directly)"
    )


def test_healthy_run_not_frozen_at_0_385():
    # The exact frozen constant from the bug: (0.7 + 0.0)/2 * 0.9 + 0.7 * 0.1
    coherence = _run_with_detector_score(1.0)
    assert abs(coherence - 0.385) > 1e-9
