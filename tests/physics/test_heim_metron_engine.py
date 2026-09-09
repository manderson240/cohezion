"""Unit tests for Burkhard Heim Metron Area Invariant & Polymetric Tensor Engine."""

from __future__ import annotations

import math

import numpy as np

from cohezion.physics.heim_metron_engine import (
    METRON_TAU,
    HeimMetronEngine,
    HeimState12D,
)


def test_metron_quantum_constant() -> None:
    # Check that tau is in the range ~6.15e-70 m^2
    assert 6.0e-70 < METRON_TAU < 6.3e-70


def test_surface_area_quantization() -> None:
    engine = HeimMetronEngine()
    test_area = 1.23e-69  # approx 2 metrons
    n_metrons, quantized_area = engine.quantize_surface_area(test_area)
    assert n_metrons == 2
    assert math.isclose(quantized_area, 2 * METRON_TAU, rel_tol=1e-5)


def test_heim_12d_state_from_flume() -> None:
    flume_vec = np.array([1.0, 2.0, 3.0, 0.0, 0.5, 0.5, 0.1, 0.2, 0.8, 0.7, 0.6, 0.9])
    state = HeimState12D.from_flume_vector(flume_vec)
    assert state.x1 == 1.0
    assert state.x5_entelechy == 0.5
    assert state.x12_g4 == 0.9
    np.testing.assert_allclose(state.to_vector(), flume_vec)


def test_polymetric_distance_and_syntrometrie() -> None:
    engine = HeimMetronEngine()
    s1 = HeimState12D.from_flume_vector(np.ones(12))
    s2 = HeimState12D.from_flume_vector(np.zeros(12))

    dist = engine.compute_polymetric_distance(s1, s2)
    assert dist > 0.0

    synth = engine.project_syntrometric_force(s1)
    assert "s2_entelechy_norm" in synth
    assert "g4_informational_norm" in synth
    assert "syntrometrie_coupling" in synth
    assert 0.0 <= synth["hiho_coherence"] <= 1.0
