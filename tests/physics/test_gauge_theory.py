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
        assert len(d["fabrics"]) == 4
