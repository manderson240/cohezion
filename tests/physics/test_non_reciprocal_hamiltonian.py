"""Tests for NonReciprocalHamiltonian — Shi et al. 2026 embedding."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.non_reciprocal_hamiltonian import (
    NonReciprocalHamiltonian,
    make_flume_vae_hamiltonian,
    make_triune_routing_hamiltonian,
)


# ── Fixture ────────────────────────────────────────────────────────────────


@pytest.fixture
def skew_2d() -> NonReciprocalHamiltonian:
    """2-DOF purely antisymmetric coupling: J = [[0,1],[-1,0]]."""
    J = np.array([[0.0, 1.0], [-1.0, 0.0]])
    return NonReciprocalHamiltonian(coupling_matrix=J)


@pytest.fixture
def mixed_3d() -> NonReciprocalHamiltonian:
    """3-DOF partially non-reciprocal coupling."""
    J = np.array([[0.0, 0.5, -0.3], [-0.8, 0.0, 0.6], [0.3, -0.4, 0.0]])
    return NonReciprocalHamiltonian(coupling_matrix=J)


# ── Construction ────────────────────────────────────────────────────────────


def test_symmetric_decomposition(skew_2d: NonReciprocalHamiltonian) -> None:
    """Jˢ + Jᵃ must reconstruct J exactly."""
    J_reconstructed = skew_2d.symmetric_part + skew_2d.antisymmetric_part
    J_original = np.array([[0.0, 1.0], [-1.0, 0.0]])
    np.testing.assert_allclose(J_reconstructed, J_original, atol=1e-12)


def test_symmetric_part_is_symmetric(mixed_3d: NonReciprocalHamiltonian) -> None:
    Js = mixed_3d.symmetric_part
    np.testing.assert_allclose(Js, Js.T, atol=1e-12)


def test_antisymmetric_part_is_antisymmetric(mixed_3d: NonReciprocalHamiltonian) -> None:
    Ja = mixed_3d.antisymmetric_part
    np.testing.assert_allclose(Ja, -Ja.T, atol=1e-12)


def test_invalid_coupling_raises() -> None:
    with pytest.raises(ValueError, match="square"):
        NonReciprocalHamiltonian(coupling_matrix=np.array([[1.0, 2.0, 3.0]]))


# ── Mirror constraint ───────────────────────────────────────────────────────


def test_auxiliary_state_applies_mirror_phase(skew_2d: NonReciprocalHamiltonian) -> None:
    x = np.array([0.3, 0.7])
    theta = skew_2d.auxiliary_state(x)
    np.testing.assert_allclose(theta - x, np.pi, atol=1e-12)


def test_mirror_violation_is_zero_on_constrained(skew_2d: NonReciprocalHamiltonian) -> None:
    x = np.array([0.5, 0.2])
    theta = skew_2d.auxiliary_state(x)
    violation = skew_2d.mirror_violation(x, theta)
    np.testing.assert_allclose(violation, 0.0, atol=1e-12)


def test_mirror_violation_is_nonzero_off_constraint(skew_2d: NonReciprocalHamiltonian) -> None:
    x = np.array([0.5, 0.2])
    theta = x  # wrong — should be x + π
    violation = skew_2d.mirror_violation(x, theta)
    assert np.any(np.abs(violation) > 0.1)


# ── Hamiltonian evaluation ──────────────────────────────────────────────────


def test_hamiltonian_is_finite(mixed_3d: NonReciprocalHamiltonian) -> None:
    x = np.array([0.3, 0.5, 0.7])
    H = mixed_3d.hamiltonian(x)
    assert np.isfinite(H)


def test_hamiltonian_reciprocal_case_equals_quadratic(skew_2d: NonReciprocalHamiltonian) -> None:
    """For purely antisymmetric J, Jˢ = 0 so H = xᵀ Jᵃ θ only."""
    x = np.array([1.0, 0.0])
    theta = skew_2d.auxiliary_state(x)
    H = skew_2d.hamiltonian(x, theta)
    # xᵀ Jˢ x = 0 (Jˢ=0 for skew J); xᵀ Jᵃ θ = x·Ja·(x+π)
    Ja = skew_2d.antisymmetric_part
    expected = float(x @ Ja @ theta)
    assert H == pytest.approx(expected, rel=1e-10)


# ── Force ───────────────────────────────────────────────────────────────────


def test_force_shape(skew_2d: NonReciprocalHamiltonian) -> None:
    x = np.array([0.4, 0.6])
    f = skew_2d.force(x)
    assert f.shape == x.shape


def test_force_recovers_skew_dynamics(skew_2d: NonReciprocalHamiltonian) -> None:
    """For J = [[0,1],[-1,0]], ẋ = -Jᵃ x = -J x = [-x₁, x₀]."""
    x = np.array([0.3, 0.7])
    f = skew_2d.force(x)
    # J = [[0,1],[-1,0]] is purely antisymmetric → force = -Ja·x = -J·x
    expected = -np.array([[0.0, 1.0], [-1.0, 0.0]]) @ x
    np.testing.assert_allclose(f, expected, atol=1e-12)


def test_zero_force_for_zero_state(skew_2d: NonReciprocalHamiltonian) -> None:
    x = np.zeros(2)
    np.testing.assert_allclose(skew_2d.force(x), np.zeros(2), atol=1e-12)


# ── Simulation ──────────────────────────────────────────────────────────────


def test_simulate_output_shape(skew_2d: NonReciprocalHamiltonian) -> None:
    x0 = np.array([1.0, 0.0])
    traj = skew_2d.simulate(x0, n_steps=50)
    assert traj.shape == (51, 2)


def test_simulate_initial_condition_preserved(skew_2d: NonReciprocalHamiltonian) -> None:
    x0 = np.array([0.5, 0.3])
    traj = skew_2d.simulate(x0, n_steps=10)
    np.testing.assert_allclose(traj[0], x0, atol=1e-12)


def test_simulate_with_temperature_adds_noise(skew_2d: NonReciprocalHamiltonian) -> None:
    x0 = np.array([0.5, 0.5])
    rng = np.random.default_rng(42)
    traj_noisy = skew_2d.simulate(x0, n_steps=20, temperature=0.01, rng=rng)
    traj_zero = skew_2d.simulate(x0, n_steps=20, temperature=0.0)
    assert not np.allclose(traj_noisy, traj_zero)


# ── HIHO metrics ────────────────────────────────────────────────────────────


def test_symmetrization_error_is_zero_for_symmetric_J() -> None:
    J = np.array([[0.0, 0.5], [0.5, 0.0]])  # symmetric
    h = NonReciprocalHamiltonian(coupling_matrix=J)
    assert h.symmetrization_error() == pytest.approx(0.0, abs=1e-12)


def test_symmetrization_error_nonzero_for_skew(skew_2d: NonReciprocalHamiltonian) -> None:
    assert skew_2d.symmetrization_error() > 0.0


def test_hiho_reciprocity_score_bounds() -> None:
    J = np.array([[0.0, 1.0], [-1.0, 0.0]])
    h = NonReciprocalHamiltonian(coupling_matrix=J)
    score = h.hiho_reciprocity_score()
    assert 0.0 <= score <= 1.0


def test_hiho_reciprocity_peaks_at_half_half() -> None:
    """When ‖Jˢ‖ = ‖Jᵃ‖ (ρ=0.5), score should equal 1.0."""
    # Build J where Jˢ and Jᵃ have equal Frobenius norm
    Js = np.array([[0.0, 1.0], [1.0, 0.0]]) * (1.0 / np.sqrt(2))
    Ja = np.array([[0.0, 1.0], [-1.0, 0.0]]) * (1.0 / np.sqrt(2))
    J = Js + Ja
    h = NonReciprocalHamiltonian(coupling_matrix=J)
    assert h.hiho_reciprocity_score() == pytest.approx(1.0, rel=1e-6)


def test_hiho_reciprocal_flag(skew_2d: NonReciprocalHamiltonian) -> None:
    """Purely antisymmetric J: ρ = 0 → not HIHO reciprocal."""
    assert not skew_2d.is_hiho_reciprocal()


def test_to_dict_keys(skew_2d: NonReciprocalHamiltonian) -> None:
    d = skew_2d.to_dict()
    assert {"n_dof", "symmetrization_error", "hiho_reciprocity_score", "is_hiho_reciprocal"} <= set(
        d.keys()
    )


# ── Convenience constructors ────────────────────────────────────────────────


def test_triune_routing_hamiltonian_shape() -> None:
    h = make_triune_routing_hamiltonian()
    assert h.n_dof == 3


def test_triune_routing_is_non_reciprocal() -> None:
    h = make_triune_routing_hamiltonian()
    assert h.symmetrization_error() > 0.0


def test_flume_vae_hamiltonian_shape() -> None:
    h = make_flume_vae_hamiltonian()
    assert h.n_dof == 2


def test_flume_vae_kl_asymmetry() -> None:
    """KL coupling J[0,1]=0.01 ≠ J[1,0]=1.0 → encoder/decoder not reciprocal."""
    h = make_flume_vae_hamiltonian()
    assert h.symmetrization_error() > 0.0
    # Encoder is more strongly driven than decoder (reconstruction dominates)
    Ja = h.antisymmetric_part
    assert abs(Ja[1, 0]) > 0.0


def test_simulate_triune_trajectory() -> None:
    h = make_triune_routing_hamiltonian()
    x0 = np.array([0.5, 0.5, 0.5])
    traj = h.simulate(x0, n_steps=20, dt=0.01)
    assert traj.shape == (21, 3)
    assert np.all(np.isfinite(traj))
