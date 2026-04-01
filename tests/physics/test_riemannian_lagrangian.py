"""Tests for Riemannian geometry and Lagrangian dynamics.

Verifies mathematical properties: flat metric → straight geodesics,
energy conservation, action stationarity, Christoffel symbol identities.
"""

import numpy as np
import pytest

from cohezion.physics.lagrangian import (
    LagrangianDynamics,
    Potential,
    harmonic_potential,
    hiho_potential,
)
from cohezion.physics.riemannian_metric import (
    euclidean_metric,
    fabric_block_metric,
    hiho_metric,
)


class TestEuclideanMetric:
    """Verify properties of flat (Euclidean) metric."""

    def test_euclidean_is_identity(self):
        """g_ij = δ_ij for Euclidean metric."""
        m = euclidean_metric(3)
        x = np.array([1.0, 2.0, 3.0])
        np.testing.assert_array_equal(m.evaluate(x), np.eye(3))

    def test_euclidean_inverse_is_identity(self):
        """g^ij = δ^ij for Euclidean metric."""
        m = euclidean_metric(3)
        np.testing.assert_array_equal(m.inverse(np.zeros(3)), np.eye(3))

    def test_euclidean_determinant_is_one(self):
        """det(δ_ij) = 1."""
        m = euclidean_metric(4)
        assert m.determinant(np.zeros(4)) == pytest.approx(1.0)

    def test_euclidean_norm_is_standard(self):
        """|v| = √(v·v) for Euclidean metric."""
        m = euclidean_metric(3)
        v = np.array([3.0, 4.0, 0.0])
        assert m.norm(np.zeros(3), v) == pytest.approx(5.0)

    def test_euclidean_christoffel_is_zero(self):
        """Γ^i_jk = 0 for flat metric."""
        m = euclidean_metric(3)
        gamma = m.christoffel(np.array([1.0, 2.0, 3.0]))
        np.testing.assert_allclose(gamma, 0.0, atol=1e-8)


class TestGeodesics:
    """Verify geodesic properties."""

    def test_flat_geodesic_is_straight_line(self):
        """Geodesics on flat metric are straight lines."""
        m = euclidean_metric(3)
        x0 = np.array([0.0, 0.0, 0.0])
        v0 = np.array([1.0, 2.0, 3.0])

        t, traj = m.geodesic(x0, v0, t_span=(0, 1), n_steps=50)

        # Should be straight: x(t) = x0 + v0*t
        for i, ti in enumerate(t):
            expected = x0 + v0 * ti
            np.testing.assert_allclose(traj[i], expected, atol=1e-6)

    def test_geodesic_preserves_velocity_on_flat(self):
        """Velocity is constant on flat-metric geodesics."""
        m = euclidean_metric(2)
        x0 = np.zeros(2)
        v0 = np.array([1.0, 0.5])

        t, traj = m.geodesic(x0, v0, t_span=(0, 2), n_steps=100)

        # Check velocity at each step
        for i in range(1, len(t)):
            dt = t[i] - t[i - 1]
            v_approx = (traj[i] - traj[i - 1]) / dt
            np.testing.assert_allclose(v_approx, v0, atol=1e-4)


class TestFabricMetric:
    """Verify the block-diagonal fabric metric."""

    def test_fabric_metric_block_structure(self):
        """Fabric metric has correct coupling constants per block."""
        m = fabric_block_metric(12)
        g = m.evaluate(np.zeros(12))
        assert g[0, 0] == pytest.approx(1.0)  # Space
        assert g[3, 3] == pytest.approx(0.7)  # Field
        assert g[6, 6] == pytest.approx(0.5)  # Control
        assert g[9, 9] == pytest.approx(0.3)  # Precipitation

    def test_fabric_metric_is_diagonal(self):
        """Fabric metric is diagonal (no cross-fabric coupling)."""
        m = fabric_block_metric(12)
        g = m.evaluate(np.zeros(12))
        off_diag = g - np.diag(np.diag(g))
        np.testing.assert_allclose(off_diag, 0.0, atol=1e-15)


class TestHIHOMetric:
    """Verify the HIHO-weighted metric."""

    def test_hiho_metric_peaked_at_center(self):
        """Metric is largest at HIHO point (0.5)."""
        m = hiho_metric(3)
        g_center = m.evaluate(np.full(3, 0.5))
        g_away = m.evaluate(np.full(3, 0.0))
        # Weight at center should be higher than at boundary
        assert g_center[0, 0] > g_away[0, 0]


class TestLagrangianDynamics:
    """Verify Lagrangian mechanics properties."""

    def test_free_particle_straight_line(self):
        """Free particle (V=0) on flat metric follows straight line."""
        metric = euclidean_metric(3)
        zero_potential = Potential(lambda q: 0.0, lambda q: np.zeros(3))
        dynamics = LagrangianDynamics(metric, zero_potential)

        q0 = np.array([0.0, 0.0, 0.0])
        v0 = np.array([1.0, 0.5, -0.3])

        result = dynamics.simulate(q0, v0, n_steps=100, dt=0.01)
        final_q = result["positions"][-1]

        expected = q0 + v0 * 1.0  # t = n_steps * dt = 1.0
        np.testing.assert_allclose(final_q, expected, atol=1e-4)

    def test_energy_conservation_harmonic(self):
        """Total energy is conserved for harmonic potential (no damping)."""
        metric = euclidean_metric(3)
        potential = harmonic_potential(3, k=1.0, center=np.zeros(3))
        dynamics = LagrangianDynamics(metric, potential, damping=0.0)

        q0 = np.array([1.0, 0.0, 0.0])
        v0 = np.array([0.0, 1.0, 0.0])

        result = dynamics.simulate(q0, v0, n_steps=500, dt=0.01)
        energies = result["energies"]

        # Energy should be approximately constant (Verlet preserves it)
        E0 = energies[0]
        max_drift = np.max(np.abs(energies - E0))
        assert max_drift < 0.01 * abs(E0), f"Energy drift {max_drift} exceeds 1%"

    def test_harmonic_oscillation(self):
        """Harmonic potential produces oscillatory motion."""
        metric = euclidean_metric(1)
        potential = harmonic_potential(1, k=4.0, center=np.zeros(1))
        dynamics = LagrangianDynamics(metric, potential)

        q0 = np.array([1.0])
        v0 = np.array([0.0])

        result = dynamics.simulate(q0, v0, n_steps=500, dt=0.01)
        positions = result["positions"][:, 0]

        # Should oscillate: period T = 2π/ω = 2π/2 = π ≈ 3.14
        # After half period, position should be near -1
        half_period_step = int(np.pi / 0.01 / 2)
        if half_period_step < len(positions):
            assert positions[half_period_step] < -0.5

    def test_damping_reduces_energy(self):
        """Damping causes energy to decrease over time."""
        metric = euclidean_metric(2)
        potential = harmonic_potential(2, k=1.0, center=np.zeros(2))
        dynamics = LagrangianDynamics(metric, potential, damping=0.5)

        q0 = np.array([1.0, 0.0])
        v0 = np.array([0.0, 1.0])

        result = dynamics.simulate(q0, v0, n_steps=200, dt=0.01)
        E_initial = result["energies"][0]
        E_final = result["energies"][-1]

        assert E_final < E_initial

    def test_action_integral_positive(self):
        """Action integral is finite for a valid trajectory."""
        metric = euclidean_metric(2)
        potential = harmonic_potential(2, k=1.0, center=np.zeros(2))
        dynamics = LagrangianDynamics(metric, potential)

        q0 = np.array([1.0, 0.0])
        v0 = np.array([0.0, 0.5])

        result = dynamics.simulate(q0, v0, n_steps=50, dt=0.01)
        S = dynamics.action_integral(result["positions"], dt=0.01)
        assert np.isfinite(S)


class TestHIHOPotential:
    """Verify the HIHO attractor potential."""

    def test_hiho_minimum_at_center(self):
        """V is minimized at q = 0.5 (HIHO point)."""
        pot = hiho_potential(3)
        V_center = pot.evaluate(np.full(3, 0.5))
        V_away = pot.evaluate(np.full(3, 0.0))
        assert V_center < V_away

    def test_hiho_gradient_zero_at_center(self):
        """∂V/∂q = 0 at the HIHO point (equilibrium)."""
        pot = hiho_potential(3)
        grad = pot.gradient(np.full(3, 0.5))
        np.testing.assert_allclose(grad, 0.0, atol=1e-6)

    def test_hiho_gradient_points_inward(self):
        """Gradient points toward 0.5 from both sides."""
        pot = hiho_potential(1)
        grad_above = pot.gradient(np.array([0.8]))
        grad_below = pot.gradient(np.array([0.2]))
        # Both gradients should point toward 0.5
        assert grad_above[0] > 0  # ∂V/∂q > 0 at q > 0.5 (restoring toward 0.5)
        assert grad_below[0] < 0  # ∂V/∂q < 0 at q < 0.5


class TestCurvature:
    """Verify curvature computation."""

    def test_flat_curvature_is_zero(self):
        """Ricci scalar R = 0 for Euclidean metric."""
        m = euclidean_metric(3)
        R = m.riemann_curvature_scalar(np.array([1.0, 2.0, 3.0]))
        assert abs(R) < 1e-4
