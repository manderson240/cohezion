"""Tests for QuadratureNexus oscillation detection (Task #17).

The Mycelium feedback loop can over-correct per-voice score adjustments,
producing alternating positive/negative deltas. _detect_oscillation flags
this behavior so apply_mycelium_feedback can damp the learning rate.
"""

from __future__ import annotations

from cohezion.swarm.quadrature_nexus import QuadratureNexus, VoiceType


def test_detect_oscillation_no_history():
    """An empty history returns False (no oscillation)."""
    nexus = QuadratureNexus()
    # _mycelium_calibration_history defaults to empty list per voice
    assert nexus._mycelium_calibration_history[VoiceType.ARCHITECT] == []
    assert nexus._detect_oscillation(VoiceType.ARCHITECT) is False


def test_detect_oscillation_monotone():
    """Three same-sign adjustments are not oscillation."""
    nexus = QuadratureNexus()
    nexus._mycelium_calibration_history[VoiceType.ENGINEER] = [0.1, 0.2, 0.3]
    assert nexus._detect_oscillation(VoiceType.ENGINEER) is False


def test_detect_oscillation_alternating():
    """Three sign-alternating adjustments are oscillation."""
    nexus = QuadratureNexus()
    nexus._mycelium_calibration_history[VoiceType.ETHICIST] = [0.1, -0.1, 0.1]
    assert nexus._detect_oscillation(VoiceType.ETHICIST) is True

    # Also true in the opposite phase
    nexus._mycelium_calibration_history[VoiceType.RESOURCE] = [-0.05, 0.05, -0.05]
    assert nexus._detect_oscillation(VoiceType.RESOURCE) is True


def test_detect_oscillation_two_items():
    """Need at least 3 items to detect oscillation."""
    nexus = QuadratureNexus()
    nexus._mycelium_calibration_history[VoiceType.ARCHITECT] = [0.1, -0.1]
    assert nexus._detect_oscillation(VoiceType.ARCHITECT) is False
    # And one item too
    nexus._mycelium_calibration_history[VoiceType.ARCHITECT] = [0.1]
    assert nexus._detect_oscillation(VoiceType.ARCHITECT) is False
