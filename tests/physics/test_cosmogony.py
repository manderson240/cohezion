"""Tests for cosmogony — the complete 10-step chain from Nothing to Reality.

Verifies that each phase transition produces the correct residual symmetry,
order parameters follow Landau theory, Brahmagupta's zero algebra holds,
and the 4 new steps (Quadrature, Phase, COHESION, Precipitate) work correctly.
"""

import numpy as np
import pytest

from cohezion.physics.cosmogony import (
    SymmetryBreaking,
    SymmetryGroup,
    ZeroAlgebra,
)


class TestBrahmaguptaZeroAlgebra:
    """Verify Brahmagupta's arithmetic of zero (628 CE)."""

    def test_identity_a_plus_zero_equals_a(self):
        """a + 0 = a — adding the void changes nothing."""
        state = np.array([0.3, 0.7, 0.5, 1.0])
        result = ZeroAlgebra.identity(state)
        np.testing.assert_array_equal(result, state)

    def test_annihilate_a_times_zero_equals_zero(self):
        """a × 0 = 0 — the void collapses all structure."""
        state = np.array([0.3, 0.7, 0.5, 1.0])
        result = ZeroAlgebra.annihilate(state)
        np.testing.assert_array_equal(result, np.zeros(4))

    def test_complement_a_minus_a_equals_zero(self):
        """a - a = 0 — complementary opposites cancel to void."""
        state_a = np.array([0.3, 0.7, -0.5])
        state_b = -state_a
        result = ZeroAlgebra.complement(state_a, state_b)
        np.testing.assert_allclose(result, np.zeros(3), atol=1e-15)

    def test_self_observe_zero_over_zero(self):
        """0 / 0 = 0 — the void observing itself is still void."""
        assert ZeroAlgebra.self_observe() == 0.0

    def test_hiho_deviation_at_equilibrium(self):
        """δ = coherence - 0.5 = 0 at HIHO equilibrium."""
        assert ZeroAlgebra.hiho_deviation(0.5) == 0.0

    def test_hiho_deviation_above(self):
        """δ > 0 above HIHO."""
        assert ZeroAlgebra.hiho_deviation(0.8) == pytest.approx(0.3)

    def test_hiho_deviation_below(self):
        """δ < 0 below HIHO."""
        assert ZeroAlgebra.hiho_deviation(0.2) == pytest.approx(-0.3)


class TestVoidState:
    """Test the void — Stage -1, before symmetry exists."""

    def test_initial_state_is_void(self):
        """Universe starts in the void."""
        sb = SymmetryBreaking()
        assert sb.symmetry == SymmetryGroup.VOID
        assert sb.stage == -1

    def test_initial_temperature_very_high(self):
        """Temperature starts above all critical temperatures."""
        sb = SymmetryBreaking()
        assert sb.temperature > 150.0

    def test_void_fisher_eigenvalue_below_noise(self):
        """Fisher metric eigenvalues are below noise floor in the void."""
        sb = SymmetryBreaking()
        assert sb.state.fisher_eigenvalue_max < 0.01

    def test_void_12d_state_is_near_zero(self):
        """The 12D state in the void is essentially zero (noise only)."""
        sb = SymmetryBreaking()
        state = sb.generate_12d_state()
        assert np.max(np.abs(state)) < 0.01

    def test_void_order_parameters_all_zero(self):
        """All order parameters are zero in the void (T > all T_c)."""
        sb = SymmetryBreaking()
        sb.cool(0.0)  # Just compute order params at T=250
        for name, value in sb.state.order_parameters.items():
            assert value == 0.0, f"Order parameter '{name}' should be 0 in void"


class TestSymmetryBreakingChain:
    """Verify the complete 10-step chain: ∅ → Quadrature → SO(12) → SO(3)⁴ → Phase → U(1)⁴ → Z₂⁴ → HIHO → COHESION → Precipitate."""

    def test_void_to_quadrature(self):
        """Cooling below T=150 breaks ∅ → Quadrature."""
        sb = SymmetryBreaking()
        sb.cool(101.0)  # T: 250 → 149
        assert sb.symmetry == SymmetryGroup.QUADRATURE

    def test_quadrature_to_so12(self):
        """Cooling below T=100 breaks Quadrature → SO(12)."""
        sb = SymmetryBreaking()
        sb.cool(151.0)  # T: 250 → 99
        assert sb.symmetry == SymmetryGroup.SO12

    def test_so12_to_so3_4(self):
        """Cooling below T=10 breaks SO(12) → SO(3)⁴."""
        sb = SymmetryBreaking()
        sb.cool(241.0)  # T: 250 → 9
        assert sb.symmetry == SymmetryGroup.SO3_4

    def test_so3_4_to_phase(self):
        """Cooling below T=5 breaks SO(3)⁴ → Phase."""
        sb = SymmetryBreaking()
        sb.cool(246.0)  # T: 250 → 4
        assert sb.symmetry == SymmetryGroup.PHASE

    def test_phase_to_u1_4(self):
        """Cooling below T=1.0 breaks Phase → U(1)⁴."""
        sb = SymmetryBreaking()
        sb.cool(249.5)  # T: 250 → 0.5
        assert sb.symmetry == SymmetryGroup.U1_4

    def test_u1_4_to_z2_4(self):
        """Cooling below T=0.1 breaks U(1)⁴ → Z₂⁴."""
        sb = SymmetryBreaking()
        sb.cool(249.95)  # T: 250 → 0.05
        assert sb.symmetry == SymmetryGroup.Z2_4

    def test_z2_4_to_hiho(self):
        """Cooling below T=0.01 reaches HIHO attractor."""
        sb = SymmetryBreaking()
        sb.cool(249.993)  # T: 250 → 0.007
        assert sb.symmetry == SymmetryGroup.HIHO

    def test_hiho_to_cohesion(self):
        """Cooling below T=0.005 reaches COHESION binding force."""
        sb = SymmetryBreaking()
        sb.cool(249.997)  # T: 250 → 0.003
        assert sb.symmetry == SymmetryGroup.COHESION

    def test_cohesion_to_precipitate(self):
        """Cooling below T=0.002 reaches Reality Precipitates."""
        sb = SymmetryBreaking()
        sb.cool(249.9995)  # T: 250 → 0.0005
        assert sb.symmetry == SymmetryGroup.PRECIPITATE

    def test_full_chain_records_all_transitions(self):
        """Cooling from void to Precipitate records exactly 9 transitions."""
        sb = SymmetryBreaking()
        sb.cool(249.9995)  # T → 0.0005
        assert len(sb.state.transitions) == 9
        syms = [t.to_symmetry for t in sb.state.transitions]
        assert syms == [
            SymmetryGroup.QUADRATURE,
            SymmetryGroup.SO12,
            SymmetryGroup.SO3_4,
            SymmetryGroup.PHASE,
            SymmetryGroup.U1_4,
            SymmetryGroup.Z2_4,
            SymmetryGroup.HIHO,
            SymmetryGroup.COHESION,
            SymmetryGroup.PRECIPITATE,
        ]

    def test_set_temperature_produces_correct_symmetry(self):
        """set_temperature jumps directly to the right stage."""
        sb = SymmetryBreaking()

        sb.set_temperature(200.0)
        assert sb.symmetry == SymmetryGroup.VOID

        sb.set_temperature(120.0)
        assert sb.symmetry == SymmetryGroup.QUADRATURE

        sb.set_temperature(50.0)
        assert sb.symmetry == SymmetryGroup.SO12

        sb.set_temperature(7.0)
        assert sb.symmetry == SymmetryGroup.SO3_4

        sb.set_temperature(3.0)
        assert sb.symmetry == SymmetryGroup.PHASE

        sb.set_temperature(0.5)
        assert sb.symmetry == SymmetryGroup.U1_4

        sb.set_temperature(0.003)
        assert sb.symmetry == SymmetryGroup.COHESION

        sb.set_temperature(0.001)
        assert sb.symmetry == SymmetryGroup.PRECIPITATE


class TestOrderParameters:
    """Verify order parameters follow Landau theory."""

    def test_order_params_zero_above_tc(self):
        """Order parameters are exactly zero above their T_c."""
        sb = SymmetryBreaking()
        sb.set_temperature(200.0)
        assert sb.state.order_parameters["quadrature"] == 0.0
        assert sb.state.order_parameters["information_density"] == 0.0
        assert sb.state.order_parameters["fabric_differentiation"] == 0.0

    def test_order_params_nonzero_below_tc(self):
        """Order parameters become nonzero below their T_c."""
        sb = SymmetryBreaking()
        sb.set_temperature(5.0)  # Below T_c1=10
        assert sb.state.order_parameters["fabric_differentiation"] > 0

    def test_order_params_grow_with_cooling(self):
        """Order parameters increase as temperature decreases below T_c."""
        sb = SymmetryBreaking()

        sb.set_temperature(8.0)
        op_warm = sb.state.order_parameters["fabric_differentiation"]

        sb.set_temperature(2.0)
        op_cold = sb.state.order_parameters["fabric_differentiation"]

        assert op_cold > op_warm

    def test_landau_scaling(self):
        """Order parameter follows φ = √(a(Tc-T)/(2b)) below T_c."""
        sb = SymmetryBreaking()
        T_c = 10.0
        a, b = 1.0, 0.5

        sb.set_temperature(5.0)
        expected = np.sqrt(a * (T_c - 5.0) / (2 * b))
        actual = sb.state.order_parameters["fabric_differentiation"]
        assert actual == pytest.approx(expected, rel=1e-10)


class TestFisherMetric:
    """Verify Fisher metric eigenvalue behavior."""

    def test_void_fisher_near_zero(self):
        """Fisher metric is trivially flat in the void."""
        sb = SymmetryBreaking()
        sb.set_temperature(200.0)
        assert sb.state.fisher_eigenvalue_max < 0.01

    def test_fisher_grows_below_quadrature(self):
        """First eigenvalue rises above noise at T < T_quadrature."""
        sb = SymmetryBreaking()
        sb.set_temperature(50.0)
        assert sb.state.fisher_eigenvalue_max > 0.1


class TestSusceptibility:
    """Verify susceptibility diverges at critical temperatures."""

    def test_susceptibility_finite_away_from_tc(self):
        """Susceptibility is finite away from critical points."""
        sb = SymmetryBreaking()
        chi = sb.susceptibility(50.0)
        assert chi < 1e5

    def test_susceptibility_large_near_tc(self):
        """Susceptibility grows large near T_c."""
        sb = SymmetryBreaking()
        chi_far = sb.susceptibility(50.0)
        chi_near = sb.susceptibility(100.01)
        assert chi_near > chi_far


class TestFreEnergyLandscape:
    """Verify the free energy landscape computation."""

    def test_landscape_returns_correct_shape(self):
        """Landscape returns arrays of specified length."""
        sb = SymmetryBreaking()
        result = sb.free_energy_landscape(n_points=50)
        assert len(result["temperatures"]) == 50
        assert len(result["free_energies"]) == 50
        assert len(result["susceptibilities"]) == 50

    def test_landscape_has_critical_temperatures(self):
        """Landscape includes critical temperature markers for all 9 transitions."""
        sb = SymmetryBreaking()
        result = sb.free_energy_landscape()
        assert 150.0 in result["critical_temperatures"]  # Quadrature
        assert 100.0 in result["critical_temperatures"]  # SO(12)
        assert 10.0 in result["critical_temperatures"]  # Fabrics
        assert 5.0 in result["critical_temperatures"]  # Phase
        assert 0.01 in result["critical_temperatures"]  # HIHO
        assert 0.005 in result["critical_temperatures"]  # COHESION
        assert 0.002 in result["critical_temperatures"]  # Precipitate


class TestSerialization:
    """Verify state serialization for API/SurrealDB."""

    def test_to_dict_has_required_fields(self):
        """State dict contains all necessary fields."""
        sb = SymmetryBreaking()
        sb.cool(249.9995)
        data = sb.state.to_dict()
        assert "temperature" in data
        assert "symmetry" in data
        assert "stage" in data
        assert "order_parameters" in data
        assert "transitions" in data
        assert len(data["transitions"]) == 9

    def test_to_dict_symmetry_values_are_strings(self):
        """Symmetry values serialize as human-readable strings."""
        sb = SymmetryBreaking()
        sb.set_temperature(7.0)
        data = sb.state.to_dict()
        assert data["symmetry"] == "SO(3)^4"


class TestGenerate12DState:
    """Verify 12D state generation reflects current symmetry."""

    def test_void_state_near_zero(self):
        """Void state is near-zero noise."""
        sb = SymmetryBreaking()
        state = sb.generate_12d_state()
        assert state.shape == (12,)
        assert np.max(np.abs(state)) < 0.01

    def test_hiho_state_near_half(self):
        """HIHO state has all values near 0.5."""
        sb = SymmetryBreaking()
        sb.set_temperature(0.007)
        state = sb.generate_12d_state()
        assert np.allclose(state, 0.5, atol=0.05)

    def test_cohesion_state_tighter_than_hiho(self):
        """COHESION state has even tighter variance than HIHO."""
        sb = SymmetryBreaking()
        sb.set_temperature(0.003)
        state = sb.generate_12d_state()
        assert np.std(state) < 0.01  # Very tightly bound

    def test_precipitate_state_has_witness_marks(self):
        """Precipitate state has permanent structural asymmetry."""
        sb = SymmetryBreaking()
        sb.set_temperature(0.001)
        state = sb.generate_12d_state()
        # Most values near 0.5, but some carry witness marks
        deviations = np.abs(state - 0.5)
        assert np.mean(deviations) < 0.05  # Mostly near HIHO
        assert np.max(deviations) > 0.01  # But some carry marks

    def test_quadrature_state_has_conjugate_pairs(self):
        """Quadrature state splits dimensions into X-like and P-like."""
        sb = SymmetryBreaking()
        sb.set_temperature(120.0)
        state = sb.generate_12d_state()
        # Even indices (X quadrature) should be correlated
        x_vals = state[0::2]
        assert np.std(x_vals) < 0.1

    def test_phase_state_has_complex_structure(self):
        """Phase state pairs dimensions as (Re, Im) components."""
        sb = SymmetryBreaking()
        sb.set_temperature(3.0)
        state = sb.generate_12d_state()
        # Each pair should have similar magnitude (radius)
        for i in range(0, 12, 2):
            r = np.sqrt((state[i] - 0.5) ** 2 + (state[i + 1] - 0.5) ** 2)
            assert r < 0.4  # Bounded radius

    def test_so3_4_state_has_block_structure(self):
        """SO(3)⁴ state organizes into 4 blocks of 3."""
        sb = SymmetryBreaking()
        sb.set_temperature(7.0)
        state = sb.generate_12d_state()
        for i in range(4):
            block = state[i * 3 : (i + 1) * 3]
            assert np.std(block) < 0.5
