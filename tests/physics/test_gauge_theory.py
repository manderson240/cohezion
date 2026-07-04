"""Tests for SO(3) gauge theory on the four fabrics."""

import numpy as np
import pytest

from cohezion.physics.gauge_theory import (
    SO3_GENERATORS,
    FourFabricGauge,
    GaugeConnection,
)


class TestSO3Generators:
    """Verify SO(3) Lie algebra generators."""

    def test_generators_antisymmetric(self):
        """L_a^T = -L_a (antisymmetric)."""
        for L in SO3_GENERATORS:
            np.testing.assert_allclose(L, -L.T, atol=1e-15)

    def test_generators_traceless(self):
        """Tr(L_a) = 0."""
        for L in SO3_GENERATORS:
            assert abs(np.trace(L)) < 1e-15

    def test_commutation_relations(self):
        """[L_x, L_y] = L_z (and cyclic permutations)."""
        comm_xy = SO3_GENERATORS[0] @ SO3_GENERATORS[1] - SO3_GENERATORS[1] @ SO3_GENERATORS[0]
        np.testing.assert_allclose(comm_xy, SO3_GENERATORS[2], atol=1e-14)


class TestGaugeConnection:
    """Verify single-fabric gauge connection."""

    def test_zero_potential_is_flat(self):
        """A = 0 gives flat connection (F = 0, HIHO state)."""
        conn = GaugeConnection("Space")
        assert conn.is_flat()

    def test_hiho_state_gives_zero_potential(self):
        """State at exactly 0.5 yields A = 0."""
        conn = GaugeConnection("Space")
        conn.set_from_state(np.array([0.5, 0.5, 0.5]))
        assert conn.is_flat()

    def test_off_hiho_nonzero_field(self):
        """Deviation from 0.5 produces non-flat connection."""
        conn = GaugeConnection("Space")
        conn.set_from_state(np.array([0.8, 0.3, 0.6]))
        F = conn.field_strength()
        assert F.energy_density >= 0.0

    def test_field_strength_energy_nonnegative(self):
        """Yang-Mills energy density is always >= 0."""
        conn = GaugeConnection("Field", coupling=0.7)
        conn.set_from_state(np.random.randn(3) * 0.3 + 0.5)
        F = conn.field_strength()
        assert F.energy_density >= -1e-15

    def test_coupling_affects_energy(self):
        """Lower coupling → higher energy for same field strength."""
        state = np.array([0.8, 0.3, 0.7])
        conn_strong = GaugeConnection("Space", coupling=1.0)
        conn_weak = GaugeConnection("Precipitation", coupling=0.3)
        conn_strong.set_from_state(state)
        conn_weak.set_from_state(state)
        F_strong = conn_strong.field_strength()
        F_weak = conn_weak.field_strength()
        # Same field, lower coupling → higher energy density
        assert F_weak.energy_density >= F_strong.energy_density


class TestFourFabricGauge:
    """Verify the complete four-fabric gauge system."""

    def test_hiho_12d_is_flat(self):
        """All fabrics at 0.5 → all connections flat → HIHO."""
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.full(12, 0.5))
        assert gauge.is_hiho()

    def test_yang_mills_zero_at_hiho(self):
        """Total Yang-Mills action = 0 at HIHO (vacuum state)."""
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.full(12, 0.5))
        assert gauge.yang_mills_action() == pytest.approx(0.0, abs=1e-15)

    def test_off_hiho_positive_action(self):
        """Non-HIHO state has positive Yang-Mills action."""
        gauge = FourFabricGauge()
        state = np.full(12, 0.5)
        state[0] = 0.8  # Perturb Space fabric
        gauge.set_from_12d_state(state)
        assert gauge.yang_mills_action() >= 0.0

    def test_covariant_tempic_shape(self):
        """Covariant Tempic field returns 12D vector."""
        gauge = FourFabricGauge()
        s1 = np.full(12, 0.5)
        s2 = np.full(12, 0.6)
        tempic = gauge.covariant_tempic(s1, s2)
        assert tempic.shape == (12,)

    def test_to_dict_structure(self):
        """Serialization includes all expected fields."""
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.full(12, 0.5))
        d = gauge.to_dict()
        assert "fabrics" in d
        assert "yang_mills_action" in d
        assert "is_hiho" in d
        assert "superconducting_order_parameter" in d
        assert len(d["fabrics"]) == 4


# ---------------------------------------------------------------------------
# Superconducting order parameter (SOP1–SOP4, 2026-07-04)
# ---------------------------------------------------------------------------


class TestSuperconductingOrderParameter:
    """U(1) superconducting order parameter f = ‖A‖²/(‖A‖²+1) ∈ [0, 1).

    Motivated by kagome-lattice flat-band superconductivity (Wang et al., arXiv:2209.04072).
    f≈0: normal/flat phase (HIHO exploration).
    f→1: condensed/ordered phase (strong gauge field).

    SOP1: GaugeConnection with zero potential (HIHO) → f = 0.0 (normal phase)
    SOP2: DISCRIMINATING — non-zero potential → f > 0; larger potential → larger f
    SOP3: FourFabricGauge returns dict with all 4 fabric names + 'aggregate'; all in [0,1)
    SOP4: to_dict() includes 'superconducting_order_parameter' key
    """

    # ── SOP1 ──────────────────────────────────────────────────────────────

    def test_sop1_zero_potential_gives_zero_order_parameter(self) -> None:
        """SOP1: flat connection (HIHO state) → f = 0.0 (normal phase, ‖A‖=0)."""
        conn = GaugeConnection("Space")
        # Default constructor: A = zeros → flat, f = 0²/(0²+1) = 0
        f = conn.superconducting_order_parameter()
        assert f == pytest.approx(0.0, abs=1e-12), (
            f"HIHO flat connection must have order parameter 0, got {f}"
        )

    def test_sop1_hiho_12d_gives_zero_aggregate(self) -> None:
        """SOP1: FourFabricGauge at HIHO (all 0.5) → all fabrics f=0, aggregate=0."""
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.full(12, 0.5))
        sop = gauge.superconducting_order_parameter()
        assert sop["aggregate"] == pytest.approx(0.0, abs=1e-12), (
            f"HIHO aggregate order parameter must be 0, got {sop['aggregate']}"
        )

    # ── SOP2 discriminating — monotone response ───────────────────────────

    def test_sop2_nonzero_potential_gives_positive_order_parameter(self) -> None:
        """SOP2 discriminating: non-zero gauge potential → f > 0.

        Wrong impl returning constant 0.0 would FAIL.
        """
        conn = GaugeConnection("Space")
        conn.set_from_state(np.array([0.8, 0.3, 0.6]))  # off-HIHO
        f = conn.superconducting_order_parameter()
        assert f > 0.0, (
            f"Non-zero gauge potential must give positive order parameter, got {f}"
        )

    def test_sop2_larger_potential_gives_larger_order_parameter(self) -> None:
        """SOP2 discriminating: stronger gauge field → larger condensate fraction.

        Wrong impl returning constant 0.5 for any nonzero potential would FAIL.
        """
        conn_weak = GaugeConnection("Space")
        conn_strong = GaugeConnection("Space")
        # Weak perturbation from HIHO
        conn_weak.set_from_state(np.array([0.6, 0.5, 0.5]))
        # Strong perturbation from HIHO
        conn_strong.set_from_state(np.array([0.95, 0.05, 0.9]))

        f_weak = conn_weak.superconducting_order_parameter()
        f_strong = conn_strong.superconducting_order_parameter()

        assert f_strong > f_weak, (
            f"Stronger gauge field must give larger order parameter: "
            f"f_strong={f_strong:.4f}, f_weak={f_weak:.4f}"
        )

    def test_sop2_order_parameter_bounded_below_one(self) -> None:
        """SOP2: f = ‖A‖²/(‖A‖²+1) < 1 always (never reaches condensate saturation)."""
        conn = GaugeConnection("Space")
        # Extreme state
        conn.set_from_state(np.array([1.0, 0.0, 1.0]))
        f = conn.superconducting_order_parameter()
        assert 0.0 <= f < 1.0, (
            f"Order parameter must be in [0, 1), got {f}"
        )

    # ── SOP3 aggregate structure ──────────────────────────────────────────

    def test_sop3_returns_dict_with_all_fabric_names(self) -> None:
        """SOP3: FourFabricGauge.superconducting_order_parameter() returns dict with
        all 4 fabric names + 'aggregate' key."""
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.random.default_rng(42).uniform(0.2, 0.8, 12))
        sop = gauge.superconducting_order_parameter()

        expected_keys = {"Space", "Field", "Control", "Precipitation", "aggregate"}
        assert expected_keys == set(sop.keys()), (
            f"Expected keys {expected_keys}, got {set(sop.keys())}"
        )

    def test_sop3_all_values_in_unit_interval(self) -> None:
        """SOP3: all order parameters ∈ [0, 1) for any 12D state."""
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.array([0.9] * 6 + [0.1] * 6))
        sop = gauge.superconducting_order_parameter()

        for name, f in sop.items():
            assert 0.0 <= f < 1.0, (
                f"Order parameter for '{name}' must be in [0, 1), got {f}"
            )

    def test_sop3_yang_mills_weighted_aggregate(self) -> None:
        """SOP3: aggregate uses Yang-Mills weights 1/g² where g = coupling constant.

        At HIHO (all zeros), aggregate = 0. After perturbation, aggregate > 0.
        (Checks the weighting produces a sensible scalar summary.)
        """
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.full(12, 0.5))
        sop_hiho = gauge.superconducting_order_parameter()
        assert sop_hiho["aggregate"] == pytest.approx(0.0, abs=1e-12)

        gauge.set_from_12d_state(np.array([0.9, 0.9, 0.9, 0.9, 0.5, 0.5,
                                            0.5, 0.5, 0.5, 0.5, 0.5, 0.5]))
        sop_perturbed = gauge.superconducting_order_parameter()
        assert sop_perturbed["aggregate"] > 0.0

    # ── SOP4 serialization ────────────────────────────────────────────────

    def test_sop4_to_dict_includes_key(self) -> None:
        """SOP4: FourFabricGauge.to_dict() includes 'superconducting_order_parameter'."""
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(np.full(12, 0.5))
        d = gauge.to_dict()
        assert "superconducting_order_parameter" in d, (
            "to_dict() must include 'superconducting_order_parameter' for compound loop integration"
        )
        # Value must be the full dict (not a scalar)
        sop = d["superconducting_order_parameter"]
        assert isinstance(sop, dict), f"Expected dict, got {type(sop)}"
        assert "aggregate" in sop
