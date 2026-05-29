"""Tests for extended physics substrates: BEC, MHD, Bismuth, Toroidal moments."""

from __future__ import annotations

import pytest

from cohezion.physics.bec_bridge import BECState, MercuryLattice
from cohezion.physics.mhd_plasma import BismuthDiamagnet, MHDEquilibrium
from cohezion.physics.toroidal_moment import FractalToroidalMoment


class TestBECState:
    def test_hiho_equilibrium_at_half_condensate(self):
        b = BECState(condensate_fraction=0.5)
        assert b.hiho_equilibrium() is True

    def test_hiho_false_at_extremes(self):
        assert BECState(condensate_fraction=0.0).hiho_equilibrium() is False
        assert BECState(condensate_fraction=1.0).hiho_equilibrium() is False

    def test_transition_rate_peaks_at_hiho(self):
        b = BECState(condensate_fraction=0.5)
        assert b.transition_rate() == pytest.approx(1.0, rel=1e-6)

    def test_transition_rate_vanishes_at_extremes(self):
        assert BECState(condensate_fraction=0.0).transition_rate() == pytest.approx(0.0)
        assert BECState(condensate_fraction=1.0).transition_rate() == pytest.approx(0.0)

    def test_same_kernel_as_lenr(self):
        """BEC transition rate = LENR reaction rate — universal 4x(1-x) kernel."""
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for f in [0.1, 0.3, 0.5, 0.7, 0.9]:
            bec = BECState(condensate_fraction=f)
            assert bec.transition_rate() == pytest.approx(h.reaction_rate(f), rel=1e-6)

    def test_float_precision_guard_at_boundary(self):
        """Same epsilon guard as IonicCluster (0.55 must be in HIHO band)."""
        assert BECState(condensate_fraction=0.45).hiho_equilibrium() is True
        assert BECState(condensate_fraction=0.55).hiho_equilibrium() is True
        assert BECState(condensate_fraction=0.44).hiho_equilibrium() is False
        assert BECState(condensate_fraction=0.56).hiho_equilibrium() is False

    def test_condensed_and_thermal_atoms_sum_to_total(self):
        b = BECState(condensate_fraction=0.7, atom_count=100)
        assert b.condensed_atoms + b.thermal_atoms == 100

    def test_to_ionic_cluster_mapping(self):
        b = BECState(condensate_fraction=0.48)
        cluster = b.to_ionic_cluster()
        assert cluster.plasma_density == pytest.approx(0.48, abs=1e-9)


class TestMercuryLattice:
    def test_bcs_gap_rate_peaks_at_hiho(self):
        m = MercuryLattice(coherence=0.5)
        assert m.bcs_gap_rate() == pytest.approx(1.0, rel=1e-6)

    def test_is_superconducting_at_hiho(self):
        m = MercuryLattice(coherence=0.5)
        assert m.is_superconducting() is True

    def test_not_superconducting_at_extremes(self):
        assert MercuryLattice(coherence=0.0).is_superconducting() is False
        assert MercuryLattice(coherence=1.0).is_superconducting() is False

    def test_same_kernel_as_lenr(self):
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for c in [0.2, 0.4, 0.5, 0.6, 0.8]:
            m = MercuryLattice(coherence=c)
            assert m.bcs_gap_rate() == pytest.approx(h.reaction_rate(c), rel=1e-6)


class TestMHDEquilibrium:
    def test_hiho_magnetized_at_beta_one(self):
        m = MHDEquilibrium(plasma_beta=1.0)  # β=1 → normalized 0.5 = HIHO
        assert m.hiho_magnetized() is True

    def test_hiho_false_at_extreme_beta(self):
        assert MHDEquilibrium(plasma_beta=0.0).hiho_magnetized() is False
        assert MHDEquilibrium(plasma_beta=2.0).hiho_magnetized() is False

    def test_alfven_coherence_peaks_at_beta_one(self):
        m = MHDEquilibrium(plasma_beta=1.0)
        assert m.alfven_coherence() == pytest.approx(1.0, rel=1e-6)

    def test_alfven_coherence_vanishes_at_extremes(self):
        assert MHDEquilibrium(plasma_beta=0.0).alfven_coherence() == pytest.approx(0.0)
        assert MHDEquilibrium(plasma_beta=2.0).alfven_coherence() == pytest.approx(0.0)

    def test_to_ionic_cluster_mapping(self):
        m = MHDEquilibrium(plasma_beta=1.0)
        cluster = m.to_ionic_cluster()
        assert cluster.plasma_density == pytest.approx(0.5, abs=1e-9)
        assert cluster.hiho_equilibrium() is True


class TestBismuthDiamagnet:
    def test_levitation_threshold_is_finite_positive(self):
        b = BismuthDiamagnet()
        threshold = b.levitation_threshold_tesla()
        assert threshold > 0
        assert threshold < 1e10  # reasonable for lab

    def test_diamagnetic_coherence_at_threshold(self):
        b = BismuthDiamagnet()
        threshold = b.levitation_threshold_tesla()
        b_at_threshold = BismuthDiamagnet(
            field_strength_tesla=threshold,
            magnetic_susceptibility=b.magnetic_susceptibility,
            mass_kg=b.mass_kg,
        )
        # At threshold ratio=1 → normalized β=0.5 → HIHO
        assert b_at_threshold.hiho_levitation() is True


class TestFractalToroidalMoment:
    def test_toroidal_moment_peaks_at_hiho(self):
        t_hiho = FractalToroidalMoment(coherence=0.5)
        t_zero = FractalToroidalMoment(coherence=0.0)
        t_one = FractalToroidalMoment(coherence=1.0)
        assert t_hiho.toroidal_moment_magnitude() > t_zero.toroidal_moment_magnitude()
        assert t_hiho.toroidal_moment_magnitude() > t_one.toroidal_moment_magnitude()
        assert t_zero.toroidal_moment_magnitude() == pytest.approx(0.0)

    def test_fractal_dimension_at_hiho_is_1_5(self):
        t = FractalToroidalMoment(coherence=0.5)
        assert t.fractal_dimension() == pytest.approx(1.5, rel=1e-6)

    def test_fractal_dimension_at_extremes_is_1(self):
        assert FractalToroidalMoment(coherence=0.0).fractal_dimension() == pytest.approx(1.0)
        assert FractalToroidalMoment(coherence=1.0).fractal_dimension() == pytest.approx(1.0)

    def test_time_reversal_broken_at_hiho(self):
        t = FractalToroidalMoment(coherence=0.5, ring_count=7)
        assert t.time_reversal_broken() is True

    def test_time_reversal_preserved_at_zero_coherence(self):
        t = FractalToroidalMoment(coherence=0.0)
        assert not t.time_reversal_broken()

    def test_hiho_toroidal_true_in_band(self):
        assert FractalToroidalMoment(coherence=0.5).hiho_toroidal() is True
        assert FractalToroidalMoment(coherence=0.45).hiho_toroidal() is True
        assert FractalToroidalMoment(coherence=0.55).hiho_toroidal() is True

    def test_same_hiho_kernel_as_lenr(self):
        """Toroidal moment kernel = LENR reaction rate = universal 4x(1-x)."""
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for c in [0.2, 0.5, 0.8]:
            t = FractalToroidalMoment(coherence=c, ring_count=1, major_radius_m=1.0)
            expected = h.reaction_rate(c)
            assert t.toroidal_moment_magnitude() == pytest.approx(expected, rel=1e-6)
