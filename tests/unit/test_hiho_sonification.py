"""Unit tests for HIHO Sonification engine (hiho_sonification.py)."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.governance.quadrature_nexus import QuadratureState
from cohezion.physics.hiho_sonification import (
    AudioFieldState,
    HIHOSonifier,
)


def test_coherence_distance_computation() -> None:
    """Test HIHO coherence distance computation |c - 0.5|."""
    assert HIHOSonifier.compute_coherence_distance(0.5) == 0.0
    assert HIHOSonifier.compute_coherence_distance(0.0) == 0.5
    assert HIHOSonifier.compute_coherence_distance(1.0) == 0.5
    assert HIHOSonifier.compute_coherence_distance(0.7) == pytest.approx(0.2)


def test_dissonance_calculation() -> None:
    """Test dissonance calculation at and off 0.5 HIHO coherence."""
    # At 0.5 coherence, zero perturbation -> zero dissonance
    assert HIHOSonifier.calculate_dissonance(0.0, 0.0) == 0.0

    # Off coherence -> non-zero dissonance
    assert HIHOSonifier.calculate_dissonance(0.2, 0.0) == pytest.approx(0.4)

    # Lyapunov micro-perturbations add dissonance
    assert HIHOSonifier.calculate_dissonance(0.0, 0.1) == pytest.approx(0.2)


def test_sonify_quadrature_state_perfect_coherence() -> None:
    """Test sonifying a state at 0.5 HIHO coherence."""
    sonifier = HIHOSonifier(fundamental_hz=432.0)
    q_state = QuadratureState(
        awareness=0.5,
        precision=0.5,
        creativity=0.5,
        dilation=0.5,
        coherence=0.5,
        entropy=0.5,
        stability=0.5,
        momentum=0.5,
        novelty=0.5,
        resonance=0.5,
        decay=0.5,
        synthesis=0.5,
    )
    audio_state = sonifier.sonify_quadrature_state(q_state)

    assert isinstance(audio_state, AudioFieldState)
    assert audio_state.fundamental_hz == 432.0
    assert audio_state.coherence_distance == 0.0
    assert audio_state.dissonance_index == 0.0
    assert "Space" in audio_state.fabrics
    assert "Field" in audio_state.fabrics
    assert "Control" in audio_state.fabrics
    assert "Precipitation" in audio_state.fabrics

    # Check fabric fundamental frequency ratios at 0.5 HIHO coherence
    assert audio_state.fabrics["Space"].frequency_hz == pytest.approx(432.0)
    assert audio_state.fabrics["Field"].frequency_hz == pytest.approx(540.0)  # 432 * 1.25
    assert audio_state.fabrics["Control"].frequency_hz == pytest.approx(648.0)  # 432 * 1.5
    assert audio_state.fabrics["Precipitation"].frequency_hz == pytest.approx(864.0)  # 432 * 2.0


def test_sonify_12d_array_state() -> None:
    """Test sonifying a 12D numpy array state."""
    sonifier = HIHOSonifier()
    arr = np.full(12, 0.5, dtype=np.float64)
    audio_state = sonifier.sonify_quadrature_state(arr)

    assert isinstance(audio_state, AudioFieldState)
    assert len(audio_state.fabrics) == 4


def test_generate_audio_buffer_and_json() -> None:
    """Test JSON audio buffer generation within timing bounds."""
    sonifier = HIHOSonifier(fundamental_hz=432.0)
    q_state = QuadratureState(coherence=0.5)
    audio_state = sonifier.sonify_quadrature_state(q_state)

    json_output = sonifier.to_web_audio_json(audio_state, duration_s=0.05)

    assert "metadata" in json_output
    assert "audio_field" in json_output
    assert "samples" in json_output
    assert len(json_output["samples"]) == int(44100 * 0.05)

    # Performance requirement: JSON buffer generation under 50ms
    assert json_output["metadata"]["generation_time_ms"] < 50.0
