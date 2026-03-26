"""Tests for SU(2) spinor algebra — verifying mathematical identities.

These tests verify that the spinor module implements correct quantum mechanics,
not just that code runs without errors. Each test corresponds to a mathematical
theorem or identity that MUST hold.
"""

import numpy as np
import pytest

from cohezion.physics.spinor import (
    SIGMA_X,
    SIGMA_Y,
    SIGMA_Z,
    SpinorState,
    commutator,
    verify_su2_algebra,
)


class TestSU2Algebra:
    """Verify the defining relations of su(2) Lie algebra."""

    def test_pauli_commutation_relations(self):
        """[σ_i, σ_j] = 2iε_ijk σ_k for all i, j, k."""
        assert verify_su2_algebra()

    def test_sigma_x_sigma_y_commutator(self):
        """[σ_x, σ_y] = 2iσ_z."""
        comm = commutator(SIGMA_X, SIGMA_Y)
        expected = 2j * SIGMA_Z
        np.testing.assert_allclose(comm, expected, atol=1e-14)

    def test_sigma_y_sigma_z_commutator(self):
        """[σ_y, σ_z] = 2iσ_x."""
        comm = commutator(SIGMA_Y, SIGMA_Z)
        expected = 2j * SIGMA_X
        np.testing.assert_allclose(comm, expected, atol=1e-14)

    def test_sigma_z_sigma_x_commutator(self):
        """[σ_z, σ_x] = 2iσ_y."""
        comm = commutator(SIGMA_Z, SIGMA_X)
        expected = 2j * SIGMA_Y
        np.testing.assert_allclose(comm, expected, atol=1e-14)

    def test_pauli_squared_is_identity(self):
        """σ_i² = I for all i."""
        for sigma in [SIGMA_X, SIGMA_Y, SIGMA_Z]:
            np.testing.assert_allclose(sigma @ sigma, np.eye(2), atol=1e-14)

    def test_pauli_hermitian(self):
        """σ_i† = σ_i (Hermitian)."""
        for sigma in [SIGMA_X, SIGMA_Y, SIGMA_Z]:
            np.testing.assert_allclose(sigma, sigma.conj().T, atol=1e-14)

    def test_pauli_traceless(self):
        """Tr(σ_i) = 0."""
        for sigma in [SIGMA_X, SIGMA_Y, SIGMA_Z]:
            assert abs(np.trace(sigma)) < 1e-14


class TestHIHOState:
    """Verify the HIHO state — Brahmagupta's zero on the Bloch sphere."""

    def test_hiho_charge_is_zero(self):
        """⟨σ_z⟩ = 0 for HIHO state (Brahmagupta's zero: balanced charge)."""
        hiho = SpinorState.hiho()
        assert abs(hiho.charge_polarity) < 1e-14

    def test_hiho_rotation_is_maximum(self):
        """⟨σ_x⟩ = 1 for HIHO state (full rotation alignment)."""
        hiho = SpinorState.hiho()
        assert abs(hiho.spin_rotation - 1.0) < 1e-14

    def test_hiho_precession_is_zero(self):
        """⟨σ_y⟩ = 0 for HIHO state (in phase, no wobble)."""
        hiho = SpinorState.hiho()
        assert abs(hiho.spin_precession) < 1e-14

    def test_hiho_coherence_is_one(self):
        """Coherence = 1 for HIHO state (pure state, maximum information)."""
        hiho = SpinorState.hiho()
        assert abs(hiho.coherence - 1.0) < 1e-14

    def test_hiho_deviation_is_zero(self):
        """HIHO deviation = 0 (at the equilibrium point)."""
        hiho = SpinorState.hiho()
        assert abs(hiho.hiho_deviation) < 1e-14

    def test_hiho_bloch_vector_on_equator(self):
        """HIHO Bloch vector is [1, 0, 0] — on the equator, x-axis."""
        hiho = SpinorState.hiho()
        np.testing.assert_allclose(hiho.bloch_vector, [1, 0, 0], atol=1e-14)


class TestSpinorStates:
    """Test standard spinor states and their properties."""

    def test_up_state(self):
        """|↑⟩: charge = +1, on north pole."""
        up = SpinorState.up()
        assert abs(up.charge_polarity - 1.0) < 1e-14
        assert abs(up.coherence - 1.0) < 1e-14

    def test_down_state(self):
        """|↓⟩: charge = -1, on south pole."""
        down = SpinorState.down()
        assert abs(down.charge_polarity + 1.0) < 1e-14
        assert abs(down.coherence - 1.0) < 1e-14

    def test_up_down_orthogonal(self):
        """⟨↑|↓⟩ = 0 (orthogonal states)."""
        up = SpinorState.up()
        down = SpinorState.down()
        assert abs(up.fidelity(down)) < 1e-14

    def test_normalization(self):
        """State vector is always normalized: |α|² + |β|² = 1."""
        state = SpinorState(3.0 + 1j, 2.0 - 0.5j)
        sv = state.state_vector
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-14

    def test_zero_vector_rejected(self):
        """Zero vector raises ValueError."""
        with pytest.raises(ValueError, match="zero vector"):
            SpinorState(0.0, 0.0)

    def test_from_bloch_north_pole(self):
        """θ=0, φ=0 gives |↑⟩."""
        state = SpinorState.from_bloch(0.0, 0.0)
        assert abs(state.charge_polarity - 1.0) < 1e-14

    def test_from_bloch_south_pole(self):
        """θ=π, φ=0 gives |↓⟩."""
        state = SpinorState.from_bloch(np.pi, 0.0)
        assert abs(state.charge_polarity + 1.0) < 1e-14

    def test_from_bloch_equator(self):
        """θ=π/2, φ=0 gives HIHO-like state on equator."""
        state = SpinorState.from_bloch(np.pi / 2, 0.0)
        assert abs(state.charge_polarity) < 1e-14
        assert abs(state.spin_rotation - 1.0) < 1e-14


class TestSU2Rotations:
    """Verify SU(2) rotation properties."""

    def test_rotation_preserves_norm(self):
        """SU(2) rotations preserve Bloch vector norm."""
        state = SpinorState(0.6, 0.8j)
        for angle in [0.1, 0.5, 1.0, np.pi, 2 * np.pi]:
            rotated = state.rotate(angle)
            assert abs(rotated.coherence - state.coherence) < 1e-14

    def test_precession_preserves_norm(self):
        """Precession preserves Bloch vector norm."""
        state = SpinorState(0.3 + 0.4j, 0.7 - 0.2j)
        precessed = state.precess(1.23)
        assert abs(precessed.coherence - state.coherence) < 1e-14

    def test_full_rotation_returns_to_start(self):
        """Rotation by 4π returns to original state (SU(2) double cover).

        Note: 2π gives -|ψ⟩ (global phase), 4π gives |ψ⟩.
        """
        state = SpinorState(0.6, 0.8)
        rotated = state.rotate(4 * np.pi)
        assert state.fidelity(rotated) > 1 - 1e-10

    def test_half_rotation_gives_phase(self):
        """Rotation by 2π gives global phase -1 (SU(2) double cover of SO(3))."""
        state = SpinorState.up()
        rotated = state.rotate(2 * np.pi)
        # |ψ⟩ and -|ψ⟩ have same Bloch vector
        np.testing.assert_allclose(rotated.bloch_vector, state.bloch_vector, atol=1e-10)

    def test_rotation_up_to_down(self):
        """Rotating |↑⟩ by π around x-axis gives |↓⟩ (up to phase)."""
        up = SpinorState.up()
        rotated = up.rotate(np.pi)
        assert abs(rotated.charge_polarity + 1.0) < 1e-10

    def test_compose_rotation_precession(self):
        """Rotation then precession = general SU(2) element."""
        state = SpinorState.hiho()
        composed = state.rotate(0.3).precess(0.5)
        assert abs(composed.coherence - 1.0) < 1e-14

    def test_general_su2_rotation(self):
        """Arbitrary axis rotation preserves Bloch vector norm."""
        state = SpinorState(0.5 + 0.3j, 0.7 - 0.1j)
        axis = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
        rotated = state.apply_su2(axis, 1.5)
        assert abs(rotated.coherence - state.coherence) < 1e-14


class TestCoherenceMapping:
    """Test mapping from Cohezion's logic/quantum values to spinor states."""

    def test_hiho_values_give_hiho_state(self):
        """logic=0.5, quantum=0.0 gives HIHO-like state."""
        state = SpinorState.from_coherence_values(0.5, 0.0)
        assert abs(state.charge_polarity) < 1e-10

    def test_logic_one_gives_up(self):
        """logic=1.0 maps to |↑⟩ (north pole)."""
        state = SpinorState.from_coherence_values(1.0, 0.0)
        assert abs(state.charge_polarity - 1.0) < 1e-10

    def test_logic_zero_gives_down(self):
        """logic=0.0 maps to |↓⟩ (south pole)."""
        state = SpinorState.from_coherence_values(0.0, 0.0)
        assert abs(state.charge_polarity + 1.0) < 1e-10


class TestSerialization:
    """Test dict serialization for API/SurrealDB."""

    def test_roundtrip(self):
        """to_dict → from_dict preserves state."""
        original = SpinorState(0.3 + 0.4j, 0.7 - 0.2j)
        data = original.to_dict()
        restored = SpinorState.from_dict(data)
        assert original.fidelity(restored) > 1 - 1e-10

    def test_to_dict_has_required_fields(self):
        """Dict contains all fields needed for visualization."""
        state = SpinorState.hiho()
        data = state.to_dict()
        required = {
            "alpha_real",
            "alpha_imag",
            "beta_real",
            "beta_imag",
            "bloch_vector",
            "coherence",
            "charge_polarity",
            "spin_rotation",
            "spin_precession",
            "hiho_deviation",
        }
        assert required.issubset(data.keys())
