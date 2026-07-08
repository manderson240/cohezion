import numpy as np
import pytest
from cohezion.flume.latent_gravity import LatentGravityNavigator


def test_empty_field_returns_zero():
    nav = LatentGravityNavigator()
    assert nav.n_particles == 0
    potential, force = nav.potential_and_force(np.zeros(12))
    assert potential == 0.0
    assert np.allclose(force, np.zeros(12))


def test_potential_negative_near_mass():
    np.random.seed(42)
    waypoints = [np.random.randn(12) for _ in range(10)]
    nav = LatentGravityNavigator()
    nav.update_field(waypoints, [1.0] * len(waypoints))
    potential, _ = nav.potential_and_force(np.zeros(12))
    assert potential < 0.0


def test_force_points_toward_single_mass():
    np.random.seed(42)
    waypoint = np.ones(12) * 0.5
    nav = LatentGravityNavigator()
    nav.update_field([waypoint], [1.0])
    potential, force = nav.potential_and_force(np.zeros(12))
    direction = waypoint - np.zeros(12)
    direction /= np.linalg.norm(direction)
    assert np.dot(force, direction) > 0


def test_potential_deeper_closer():
    np.random.seed(42)
    waypoint = np.ones(12) * 0.5
    nav = LatentGravityNavigator()
    nav.update_field([waypoint], [1.0])
    pos1 = waypoint - np.ones(12) * 0.2
    pos2 = waypoint - np.ones(12) * 2.0
    pot1, _ = nav.potential_and_force(pos1)
    pot2, _ = nav.potential_and_force(pos2)
    assert pot1 < pot2


def test_masses_length_mismatch_raises():
    np.random.seed(42)
    waypoints = [np.random.randn(12) for _ in range(3)]
    nav = LatentGravityNavigator()
    with pytest.raises(ValueError):
        nav.update_field(waypoints, [1.0, 2.0])


def test_vacuum_label_valid_class():
    nav = LatentGravityNavigator()
    label = nav.vacuum_label(np.zeros(12))
    assert label.label in {"instanton", "soliton", "trivial"}
