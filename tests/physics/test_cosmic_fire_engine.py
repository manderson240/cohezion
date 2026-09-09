"""Unit tests for Alice Bailey Cosmic Fire Triune & Seven Ray Engine."""

from __future__ import annotations

import numpy as np

from cohezion.physics.cosmic_fire_engine import CosmicFireEngine


def test_cosmic_fire_engine_initialization() -> None:
    engine = CosmicFireEngine()
    flume_12d = np.array([0.5] * 12)
    state = engine.calculate_triune_fires(flume_12d)

    assert state.electric_fire > 0.0
    assert state.solar_fire > 0.0
    assert state.friction_fire > 0.0
    assert np.isclose(state.electric_fire + state.solar_fire + state.friction_fire, 1.0, atol=1e-3)


def test_triune_fire_mapping_and_rays() -> None:
    engine = CosmicFireEngine()
    # High spirit/entelechy vector (Electric fire dominant)
    flume_high_will = np.array([0.1, 0.1, 0.1, 0.2, 0.2, 0.2, 0.2, 0.2, 0.9, 0.9, 0.9, 0.9])
    state = engine.calculate_triune_fires(flume_high_will)

    assert state.electric_fire > state.friction_fire
    assert state.ray_profile.ray_1_will > state.ray_profile.ray_3_active_intellect
    assert 0.0 <= state.compute_triune_equilibrium() <= 1.0
