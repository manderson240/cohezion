"""Tests for Adversarial Reality Check Bridge (Story 1-0-7).

Validates that non-agentic truth anchors can detect and flag coherence bubbles
where a swarm of EVOs reaches internal consensus that violates physics.
"""

from __future__ import annotations

import numpy as np

from cohezion.universe.hiho_unified_engine import EVOInitializationFactory
from cohezion.universe.truth_anchor import (
    CoherenceBubble,
    TruthAnchor,
    TruthAnchorValidator,
    ValidationResult,
)


# ── TruthAnchor Construction ──────────────────────────────────────


class TestTruthAnchorCreation:
    def test_hiho_anchor_has_expected_value(self):
        """HIHO spring constant anchor should be k=2.0."""
        anchor = TruthAnchor.hiho_spring_constant()
        assert anchor.name == "hiho_spring_constant"
        assert anchor.expected_value == 2.0

    def test_coherence_target_anchor(self):
        """Coherence target anchor should be 0.5."""
        anchor = TruthAnchor.coherence_target()
        assert anchor.name == "coherence_target"
        assert anchor.expected_value == 0.5

    def test_energy_conservation_anchor(self):
        """Energy conservation anchor: total energy should be conserved within tolerance."""
        anchor = TruthAnchor.energy_conservation()
        assert anchor.name == "energy_conservation"
        assert anchor.tolerance > 0


# ── Validator: Healthy Swarm ──────────────────────────────────────


class TestHealthySwarm:
    def test_healthy_swarm_passes_validation(self):
        """A swarm at HIHO equilibrium should pass all truth anchor checks."""
        evos = [EVOInitializationFactory.create_evo(seed=i) for i in range(4)]
        vectors = [np.random.default_rng(i).standard_normal(12) * 0.1 for i in range(4)]

        validator = TruthAnchorValidator()
        result = validator.validate(evos, vectors)

        assert result.passed is True
        assert len(result.bubbles) == 0

    def test_returns_validation_result_type(self):
        """validate() should return a ValidationResult dataclass."""
        validator = TruthAnchorValidator()
        result = validator.validate([], [])
        assert isinstance(result, ValidationResult)


# ── Validator: Coherence Bubble Detection ─────────────────────────


class TestCoherenceBubbleDetection:
    def test_detects_unanimous_high_coherence(self):
        """Swarm where all EVOs have coherence >0.95 is a bubble."""
        evos = []
        for i in range(6):
            evo = EVOInitializationFactory.create_evo(seed=i)
            evo.coherence = 0.98  # Artificially locked near 1.0
            evos.append(evo)
        vectors = [np.ones(12) * 0.5 for _ in range(6)]

        validator = TruthAnchorValidator()
        result = validator.validate(evos, vectors)

        assert result.passed is False
        assert any(b.anchor_name == "coherence_target" for b in result.bubbles)

    def test_detects_unanimous_low_coherence(self):
        """Swarm where all EVOs have coherence <0.05 is a bubble."""
        evos = []
        for i in range(6):
            evo = EVOInitializationFactory.create_evo(seed=i)
            evo.coherence = 0.02
            evos.append(evo)
        vectors = [np.zeros(12) for _ in range(6)]

        validator = TruthAnchorValidator()
        result = validator.validate(evos, vectors)

        assert result.passed is False
        assert any(b.anchor_name == "coherence_target" for b in result.bubbles)

    def test_detects_zero_variance_coherence(self):
        """All EVOs with identical coherence far from 0.5 is suspicious."""
        evos = []
        for i in range(8):
            evo = EVOInitializationFactory.create_evo(seed=i)
            evo.coherence = 0.85  # All identical, far from target
            evos.append(evo)
        vectors = [np.ones(12) for _ in range(8)]

        validator = TruthAnchorValidator()
        result = validator.validate(evos, vectors)

        assert result.passed is False

    def test_mixed_coherence_passes(self):
        """Swarm with natural variance around 0.5 should pass."""
        rng = np.random.default_rng(42)
        evos = []
        for i in range(8):
            evo = EVOInitializationFactory.create_evo(seed=i)
            # Natural spread around 0.5
            evo.coherence = float(np.clip(0.5 + rng.normal(0, 0.1), 0.1, 0.9))
            evos.append(evo)
        vectors = [rng.standard_normal(12) * 0.3 for _ in range(8)]

        validator = TruthAnchorValidator()
        result = validator.validate(evos, vectors)

        assert result.passed is True


# ── Validator: HIHO Restoring Force Check ─────────────────────────


class TestHIHORestoringForceCheck:
    def test_restoring_force_applied_correctly(self):
        """After one HIHO tick, coherence should move toward 0.5."""
        evo = EVOInitializationFactory.create_evo(seed=0)
        evo.coherence = 0.8  # Displaced from equilibrium

        validator = TruthAnchorValidator()
        result = validator.check_restoring_force(evo, dt=0.1)

        # Force should pull coherence toward 0.5
        assert result.new_coherence < 0.8
        assert result.force_applied < 0  # Restoring toward 0.5

    def test_restoring_force_zero_at_equilibrium(self):
        """At coherence=0.5, restoring force should be ~0."""
        evo = EVOInitializationFactory.create_evo(seed=0)
        evo.coherence = 0.5

        validator = TruthAnchorValidator()
        result = validator.check_restoring_force(evo, dt=0.1)

        assert abs(result.force_applied) < 1e-10


# ── CoherenceBubble Dataclass ─────────────────────────────────────


class TestCoherenceBubble:
    def test_bubble_contains_diagnostic_info(self):
        bubble = CoherenceBubble(
            anchor_name="coherence_target",
            expected=0.5,
            observed=0.98,
            severity=0.96,
            description="Unanimous high coherence",
        )
        assert bubble.severity > 0.5
        assert "coherence" in bubble.anchor_name
