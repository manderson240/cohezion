"""Tests for Observer Patch Holography bridge.

TDD: These tests validate OPH axiom mappings to SPIN coherence.
"""

import math
import pytest
from cohezion.physics.spinor import SpinorState
from cohezion.physics.observer_patch import (
    ObserverPatch,
    overlap_fraction,
    verify_observer_consistency,
    evo_observer_consistency,
    ConsistencyResult,
)


class TestOverlapFraction:
    """OPH Axiom 2: where patches overlap, descriptions must agree."""

    def test_identical_patches_full_overlap(self):
        hiho = SpinorState.hiho()
        a = ObserverPatch(agent_id="a", spinor=hiho)
        b = ObserverPatch(agent_id="b", spinor=hiho)
        assert overlap_fraction(a, b) == pytest.approx(1.0)

    def test_opposite_poles_no_overlap(self):
        a = ObserverPatch(agent_id="a", spinor=SpinorState.up(), angular_radius=math.pi / 6)
        b = ObserverPatch(agent_id="b", spinor=SpinorState.down(), angular_radius=math.pi / 6)
        assert overlap_fraction(a, b) == pytest.approx(0.0)

    def test_partial_overlap_between_zero_and_one(self):
        a = ObserverPatch(agent_id="a", spinor=SpinorState.from_bloch(math.pi / 4, 0))
        b = ObserverPatch(agent_id="b", spinor=SpinorState.from_bloch(math.pi / 3, 0))
        frac = overlap_fraction(a, b)
        assert 0 < frac < 1

    def test_overlap_is_symmetric(self):
        a = ObserverPatch(agent_id="a", spinor=SpinorState.from_bloch(0.5, 0))
        b = ObserverPatch(agent_id="b", spinor=SpinorState.from_bloch(1.0, 0))
        assert overlap_fraction(a, b) == pytest.approx(overlap_fraction(b, a))


class TestVerifyObserverConsistency:
    """Verify consistency check produces correct coherence assessments."""

    def test_hiho_agents_are_coherent(self):
        result = evo_observer_consistency("a", SpinorState.hiho(), "b", SpinorState.hiho())
        assert result.coherent is True
        assert result.consistency_score > 0.9

    def test_opposite_agents_are_decoherent(self):
        result = evo_observer_consistency("a", SpinorState.up(), "b", SpinorState.down())
        assert result.coherent is False
        assert result.overlap_fraction == 0.0

    def test_consistency_score_bounded(self):
        """Consistency must be in [0, 1]."""
        for theta in [0.1, 0.5, 1.0, 2.0, 3.0]:
            s = SpinorState.from_bloch(theta, 0)
            result = evo_observer_consistency("a", s, "b", SpinorState.hiho())
            assert 0.0 <= result.consistency_score <= 1.0

    def test_hiho_threshold_at_half(self):
        """HIHO threshold: consistency > 0.5 is coherent (Axiom 3: Local MaxEnt)."""
        result = evo_observer_consistency("a", SpinorState.hiho(), "b", SpinorState.hiho())
        assert result.consistency_score > 0.5
        assert result.coherent is True


class TestConsistencyResult:
    """ConsistencyResult data integrity."""

    def test_no_overlap_has_zero_fidelity(self):
        result = evo_observer_consistency(
            "a", SpinorState.up(), "b", SpinorState.down(),
            angular_radius=math.pi / 6,
        )
        assert result.fidelity == 0.0
        assert result.detail != ""
