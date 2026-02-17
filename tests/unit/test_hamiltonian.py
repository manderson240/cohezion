"""Tests for Hamiltonian dynamics (cohezion.physics.hamiltonian)."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.hamiltonian import HamiltonianDynamics, PotentialType


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def z0(rng):
    return rng.normal(0.5, 0.1, (10, 256)).astype(np.float32)


class TestHamiltonianDynamics:
    def test_double_well_init(self):
        hd = HamiltonianDynamics(PotentialType.DOUBLE_WELL)
        assert hd.dt == 0.01
        assert hd.temperature == 0.01
        assert hd.target == 0.5

    def test_step_preserves_shape(self, z0):
        hd = HamiltonianDynamics()
        z1 = hd.step(z0)
        assert z1.shape == z0.shape
        assert z1.dtype == np.float32

    def test_simulate_runs(self, z0):
        hd = HamiltonianDynamics()
        z_final = hd.simulate(z0, epochs=50, seed=42)
        assert z_final.shape == z0.shape

    def test_mean_stays_near_target(self, z0):
        hd = HamiltonianDynamics(PotentialType.HARMONIC, dt=0.01, temperature=0.001)
        z_final = hd.simulate(z0, epochs=500, seed=42)
        # With harmonic potential and low temperature, mean should converge to target
        assert abs(z_final.mean() - 0.5) < 0.1

    def test_energy_at_target_is_minimum(self):
        hd = HamiltonianDynamics(PotentialType.HARMONIC)
        z_target = np.full((1, 256), 0.5, dtype=np.float32)
        z_off = np.full((1, 256), 0.8, dtype=np.float32)
        e_target = hd.energy(z_target).mean()
        e_off = hd.energy(z_off).mean()
        assert e_target < e_off

    def test_double_well_equilibrium(self, z0):
        hd = HamiltonianDynamics(PotentialType.DOUBLE_WELL, dt=0.01, temperature=0.005)
        z_final = hd.simulate(z0, epochs=1000, seed=42)
        # After long simulation, agents should cluster near potential minima
        # which are near the target for the double-well
        assert z_final.std() < z0.std() * 3  # Shouldn't diverge wildly (thermal noise spreads)

    def test_trajectory_checkpoints(self, z0):
        hd = HamiltonianDynamics()
        traj = hd.simulate_with_trajectory(z0, epochs=50, checkpoint_interval=10)
        assert len(traj) == 6  # Initial + 5 checkpoints (10,20,30,40,50)
        assert traj[0][0] == 0
        assert traj[-1][0] == 50

    def test_hiho_well_potential(self):
        hd = HamiltonianDynamics(PotentialType.HIHO_WELL)
        z = np.linspace(0.0, 1.0, 100).reshape(1, -1).astype(np.float32)
        e, _g = hd._hiho_well(z)
        # Energy should be lowest near 0.5
        mid_idx = 50
        assert e[0, mid_idx] < e[0, 0]
        assert e[0, mid_idx] < e[0, -1]

    def test_custom_potential(self):
        def my_potential(z):
            energy = z * z
            gradient = 2 * z
            return energy, gradient

        hd = HamiltonianDynamics(potential=my_potential)
        z0 = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        z1 = hd.step(z0)
        assert z1.shape == z0.shape

    def test_clamp_in_simulate(self, z0):
        hd = HamiltonianDynamics(temperature=100.0)  # Very high noise
        z_final = hd.simulate(z0, epochs=10, seed=42, clamp=(-2.0, 2.0))
        assert z_final.min() >= -2.0
        assert z_final.max() <= 2.0
