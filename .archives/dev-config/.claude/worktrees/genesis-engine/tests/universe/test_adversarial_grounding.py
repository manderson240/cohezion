"""Tests for Adversarial Reality Grounding (Story 5.9, FR20)."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.universe.adversarial_grounding import (
    AdversarialGrounding,
)


class TestAdversarialGrounding:
    def test_normal_response_not_suspicious(self):
        """Manifold that responds to perturbation is healthy."""
        grounding = AdversarialGrounding(suspicion_threshold=0.02)
        result = grounding.inject_perturbation(
            coherence_before=0.5,
            coherence_after=0.45,  # Responded with delta=0.05
        )
        assert not result.suspicious
        assert len(grounding.alerts) == 0

    def test_suspicious_stability_triggers_alert(self):
        """Manifold that doesn't respond is suspicious."""
        grounding = AdversarialGrounding(suspicion_threshold=0.02)
        result = grounding.inject_perturbation(
            coherence_before=0.5,
            coherence_after=0.501,  # Barely moved: delta=0.001
        )
        assert result.suspicious
        assert len(grounding.alerts) == 1

    def test_alert_contains_description(self):
        """Hallucination alerts have descriptive messages."""
        grounding = AdversarialGrounding(suspicion_threshold=0.05)
        grounding.inject_perturbation(0.5, 0.51)
        alert = grounding.alerts[0]
        assert "hallucination" in alert.description.lower()

    def test_perturbation_vector_is_12d(self):
        """Generated perturbation vector is 12D."""
        grounding = AdversarialGrounding(magnitude=0.1)
        vec = grounding.generate_perturbation_vector(rng=np.random.default_rng(42))
        assert vec.shape == (12,)
        assert np.linalg.norm(vec) == pytest.approx(0.1, abs=1e-10)

    def test_history_accumulates(self):
        """All perturbation results are tracked."""
        grounding = AdversarialGrounding()
        grounding.inject_perturbation(0.5, 0.4)
        grounding.inject_perturbation(0.5, 0.3)
        assert len(grounding.history) == 2

    def test_resync_after_consecutive_alerts(self):
        """Resync triggered after 3 consecutive alerts."""
        grounding = AdversarialGrounding(suspicion_threshold=0.1)
        for _ in range(3):
            grounding.inject_perturbation(0.5, 0.5)  # No response
        assert grounding.should_resync(consecutive_alerts=3)

    def test_no_resync_with_few_alerts(self):
        """Resync not triggered with insufficient alerts."""
        grounding = AdversarialGrounding(suspicion_threshold=0.1)
        grounding.inject_perturbation(0.5, 0.5)
        assert not grounding.should_resync(consecutive_alerts=3)

    def test_custom_magnitude(self):
        """Perturbation magnitude is configurable."""
        grounding = AdversarialGrounding(magnitude=0.5)
        vec = grounding.generate_perturbation_vector(rng=np.random.default_rng(0))
        assert np.linalg.norm(vec) == pytest.approx(0.5, abs=1e-10)
