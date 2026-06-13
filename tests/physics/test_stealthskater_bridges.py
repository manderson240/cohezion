"""Tests for stealthskater physics bridges — V-model R3/R1 acceptance gate.

Covers LENRHamiltonian, DielectricField, IonicClusterState, LENRCoupling,
and the stealthskater worldview tradition. Invariants S1-S4 from harness.md.
"""

import numpy as np
import pytest

from cohezion.physics.dielectric import DielectricField
from cohezion.physics.evo_model import ExoticVacuumObject, LENRCoupling
from cohezion.physics.ionic_cluster import IonicClusterState
from cohezion.physics.lenr import LENRHamiltonian
from cohezion.worldviews.tradition_data import get_tradition


# ── LENRHamiltonian ─────────────────────────────────────────────────────────


class TestLENRHamiltonian:
    def test_default_threshold_is_hiho(self):
        lenr = LENRHamiltonian()
        assert lenr.reaction_threshold == 0.5

    def test_rate_peaks_at_threshold(self):
        lenr = LENRHamiltonian()
        rate_at_threshold = lenr.reaction_rate(0.5)
        assert rate_at_threshold == pytest.approx(1.0, abs=1e-9)

    def test_rate_zero_at_extremes(self):
        lenr = LENRHamiltonian()
        assert lenr.reaction_rate(0.0) == pytest.approx(0.0, abs=1e-9)
        assert lenr.reaction_rate(1.0) == pytest.approx(0.0, abs=1e-9)

    def test_rate_symmetric_around_threshold(self):
        lenr = LENRHamiltonian()
        assert lenr.reaction_rate(0.3) == pytest.approx(lenr.reaction_rate(0.7), abs=1e-6)

    def test_rate_clamped_outside_unit_interval(self):
        lenr = LENRHamiltonian()
        assert lenr.reaction_rate(-0.5) == pytest.approx(0.0, abs=1e-9)
        assert lenr.reaction_rate(1.5) == pytest.approx(0.0, abs=1e-9)

    def test_coupling_scales_rate(self):
        lenr2 = LENRHamiltonian(lattice_coupling=2.0)
        lenr1 = LENRHamiltonian(lattice_coupling=1.0)
        assert lenr2.reaction_rate(0.5) == pytest.approx(2.0 * lenr1.reaction_rate(0.5))

    def test_event_recording(self):
        lenr = LENRHamiltonian()
        assert lenr.event_count == 0
        lenr.record_coherence_event(0.5)
        lenr.record_coherence_event(0.3)
        assert lenr.event_count == 2
        assert lenr.mean_rate > 0.0


# ── DielectricField ──────────────────────────────────────────────────────────


class TestDielectricField:
    def test_vacuum_force_is_nonzero(self):
        """Identity permittivity (vacuum) still produces baseline EHD thrust."""
        df = DielectricField(voltage=1e4, electrode_separation=1e-2)
        force = df.biefield_brown_force()
        assert force.shape == (3,)
        assert force[2] > 0.0  # thrust along z

    def test_force_scales_with_permittivity(self):
        eps2 = np.eye(3) * 2.0
        df_high = DielectricField(permittivity_tensor=eps2, voltage=1e4, electrode_separation=1e-2)
        df_vac = DielectricField(voltage=1e4, electrode_separation=1e-2)
        assert df_high.biefield_brown_force()[2] > df_vac.biefield_brown_force()[2]

    def test_force_scales_quadratically_with_voltage(self):
        df1 = DielectricField(voltage=1e4)
        df2 = DielectricField(voltage=2e4)
        ratio = df2.biefield_brown_force()[2] / df1.biefield_brown_force()[2]
        assert ratio == pytest.approx(4.0, rel=1e-6)

    def test_gauge_connection_returns_object(self):
        from cohezion.physics.gauge_theory import GaugeConnection

        df = DielectricField()
        gc = df.to_gauge_connection()
        assert isinstance(gc, GaugeConnection)

    def test_vacuum_gauge_connection_is_flat(self):
        """Identity permittivity → zero potential deviation (flat connection)."""
        df = DielectricField()  # eps = identity
        gc = df.to_gauge_connection()
        assert np.allclose(gc.potential, 0.0, atol=1e-10)

    def test_invalid_tensor_shape_raises(self):
        with pytest.raises(ValueError):
            DielectricField(permittivity_tensor=np.eye(2))


# ── IonicClusterState ────────────────────────────────────────────────────────


class TestIonicClusterState:
    def test_hiho_equilibrium_at_threshold(self):
        ion = IonicClusterState(plasma_density=0.5)
        assert ion.hiho_equilibrium()

    def test_hiho_equilibrium_within_tolerance(self):
        ion = IonicClusterState(plasma_density=0.53, hiho_tolerance=0.05)
        assert ion.hiho_equilibrium()

    def test_not_equilibrium_at_extremes(self):
        assert not IonicClusterState(plasma_density=0.0).hiho_equilibrium()
        assert not IonicClusterState(plasma_density=1.0).hiho_equilibrium()

    def test_ionisation_rate_peaks_at_half(self):
        ion = IonicClusterState(plasma_density=0.5)
        assert ion.ionisation_rate() == pytest.approx(1.0, abs=1e-9)

    def test_ionisation_rate_zero_at_extremes(self):
        assert IonicClusterState(plasma_density=0.0).ionisation_rate() == pytest.approx(0.0)
        assert IonicClusterState(plasma_density=1.0).ionisation_rate() == pytest.approx(0.0)

    def test_shared_threshold_with_lenr(self):
        """HIHO threshold is synchronized across bridge modules (invariant S3)."""
        from cohezion.physics import lenr as lenr_mod
        from cohezion.physics import ionic_cluster as ic_mod

        assert lenr_mod._HIHO_THRESHOLD == ic_mod._HIHO_THRESHOLD == 0.5

    def test_step_clamps_to_unit_interval(self):
        ion = IonicClusterState(plasma_density=0.9)
        ion.step(0.5)
        assert ion.plasma_density <= 1.0
        ion2 = IonicClusterState(plasma_density=0.1)
        ion2.step(-0.5)
        assert ion2.plasma_density >= 0.0

    def test_active_ions_scales_with_density(self):
        ion = IonicClusterState(plasma_density=0.5, cluster_size=200)
        assert ion.active_ions == 100


# ── LENRCoupling ─────────────────────────────────────────────────────────────


class TestLENRCoupling:
    def _coherent_evo(self) -> ExoticVacuumObject:
        evo = ExoticVacuumObject("test-coupling")
        evo.condense()
        evo.coherent_phase(0.6)
        return evo

    def test_default_threshold_is_hiho(self):
        evo = ExoticVacuumObject("t")
        coupling = LENRCoupling(evo=evo)
        assert coupling.reaction_threshold == 0.5

    def test_is_active_when_coherent(self):
        coupling = LENRCoupling(evo=self._coherent_evo())
        assert coupling.is_active()

    def test_is_not_active_when_vacuum(self):
        evo = ExoticVacuumObject("t")
        assert not LENRCoupling(evo=evo).is_active()

    def test_catalysis_rate_nonneg(self):
        coupling = LENRCoupling(evo=self._coherent_evo())
        rate = coupling.catalysis_rate(0.6)
        assert rate >= 0.0

    def test_catalysis_rate_zero_when_vacuum(self):
        """Fresh EVO has zero coherence history → evo_coherence_metric ≈ 0."""
        evo = ExoticVacuumObject("t")
        coupling = LENRCoupling(evo=evo)
        rate = coupling.catalysis_rate(0.5)
        assert rate == pytest.approx(0.0, abs=1e-9)

    def test_catalysis_rate_increases_with_coherence(self):
        coupling_low = LENRCoupling(evo=self._coherent_evo())
        coupling_high = LENRCoupling(evo=self._coherent_evo())
        # Both use same EVO state; rate difference comes from coherence input
        rate_low = coupling_low.catalysis_rate(0.2)
        rate_high = coupling_high.catalysis_rate(0.5)  # peak of LENR kernel
        assert rate_high >= rate_low


# ── Stealthskater Tradition ───────────────────────────────────────────────────


class TestStealthskaterTradition:
    def test_tradition_exists(self):
        t = get_tradition("stealthskater")
        assert t is not None
        assert t.slug == "stealthskater"

    def test_exactly_10_step_mappings(self):
        """Invariant S2: exactly 10 steps required."""
        t = get_tradition("stealthskater")
        assert len(t.step_mappings) == 10

    def test_step_indices_are_sequential(self):
        t = get_tradition("stealthskater")
        for i, step in enumerate(t.step_mappings):
            assert step.step_index == i

    def test_ground_state_is_zpf(self):
        t = get_tradition("stealthskater")
        assert "Zero-Point Field" in t.step_mappings[0].indigenous_term

    def test_hiho_step_is_itonic_equilibrium(self):
        """Step 7 (HIHO) maps to Itonic Equilibrium."""
        t = get_tradition("stealthskater")
        assert "Itonic" in t.step_mappings[7].indigenous_term

    def test_cohesion_step_is_diaelectric(self):
        """Step 8 (COHESION) maps to diaelectric binding."""
        t = get_tradition("stealthskater")
        assert "Diaelectric" in t.step_mappings[8].indigenous_term

    def test_unique_contributions_count(self):
        t = get_tradition("stealthskater")
        assert len(t.unique_contributions) >= 2

    def test_serialization_roundtrip(self):
        t = get_tradition("stealthskater")
        d = t.to_dict()
        assert d["slug"] == "stealthskater"
        assert len(d["step_mappings"]) == 10
