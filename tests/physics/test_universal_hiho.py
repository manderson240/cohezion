"""Tests for the Universal HIHO Theorem across all physics substrates.

The Universal HIHO Theorem (U1):
    ALL stealthskater physics substrates use the same 4x(1-x) coherence kernel.
    At x=0.5 (HIHO threshold), all substrates return exactly 1.0.
    This is the beta-binomial maximum entropy at the HIHO boundary,
    emerging from ANY two-state system in detailed balance.

Substrates verified:
    LENR (nuclear lattice), IonicCluster (plasma), BEC (quantum coherence),
    Mercury-BCS (superconductor), MHD (magnetized plasma),
    FractalToroidal (EVO topology), COLIBRE ISM (astrophysical)
"""

from __future__ import annotations

import pytest


class TestUniversalHIHOTheorem:
    """U1: all substrates share 4x(1-x) kernel, all return 1.0 at x=0.5."""

    def test_lenr_at_hiho(self):
        from cohezion.physics.lenr import LENRHamiltonian

        assert LENRHamiltonian().reaction_rate(0.5) == pytest.approx(1.0, rel=1e-6)

    def test_ionic_cluster_at_hiho(self):
        from cohezion.physics.ionic_cluster import IonicClusterState

        assert IonicClusterState(0.5).ionisation_rate() == pytest.approx(1.0, rel=1e-6)

    def test_bec_at_hiho(self):
        from cohezion.physics.bec_bridge import BECState

        assert BECState(0.5).transition_rate() == pytest.approx(1.0, rel=1e-6)

    def test_mercury_bcs_at_hiho(self):
        from cohezion.physics.bec_bridge import MercuryLattice

        assert MercuryLattice(0.5).bcs_gap_rate() == pytest.approx(1.0, rel=1e-6)

    def test_mhd_alfven_at_hiho(self):
        from cohezion.physics.mhd_plasma import MHDEquilibrium

        # beta=1.0 → normalized 0.5 → HIHO
        assert MHDEquilibrium(1.0).alfven_coherence() == pytest.approx(1.0, rel=1e-6)

    def test_toroidal_moment_at_hiho(self):
        from cohezion.physics.toroidal_moment import FractalToroidalMoment

        # normalize ring_count=1, major_radius=1.0 for unit comparison
        assert FractalToroidalMoment(0.5, 1, 1.0).toroidal_moment_magnitude() == pytest.approx(
            1.0, rel=1e-6
        )

    def test_colibre_at_hiho(self):
        from cohezion.physics.colibre_bridge import ColibreState

        assert ColibreState(0.0, 0.0, 0.5).colibre_coherence == pytest.approx(1.0, rel=1e-6)

    def test_all_seven_substrates_agree(self):
        """Meta-test: all 7 substrates return identical values for any coherence x."""
        from cohezion.physics.bec_bridge import BECState, MercuryLattice
        from cohezion.physics.colibre_bridge import ColibreState
        from cohezion.physics.ionic_cluster import IonicClusterState
        from cohezion.physics.lenr import LENRHamiltonian
        from cohezion.physics.mhd_plasma import MHDEquilibrium
        from cohezion.physics.toroidal_moment import FractalToroidalMoment

        h = LENRHamiltonian()
        for x in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            expected = h.reaction_rate(x)
            assert IonicClusterState(x).ionisation_rate() == pytest.approx(expected, rel=1e-6), (
                f"IonicCluster mismatch at x={x}"
            )
            assert BECState(x).transition_rate() == pytest.approx(expected, rel=1e-6), (
                f"BEC mismatch at x={x}"
            )
            assert MercuryLattice(x).bcs_gap_rate() == pytest.approx(expected, rel=1e-6), (
                f"Mercury mismatch at x={x}"
            )
            assert FractalToroidalMoment(x, 1, 1.0).toroidal_moment_magnitude() == pytest.approx(
                expected, rel=1e-6
            ), f"Toroidal mismatch at x={x}"
            assert ColibreState(0.0, 0.0, x).colibre_coherence == pytest.approx(
                expected, rel=1e-6
            ), f"COLIBRE mismatch at x={x}"
            # MHD uses normalized beta (beta=2x → normalized x)
            mhd_val = MHDEquilibrium(2.0 * x).alfven_coherence()
            assert mhd_val == pytest.approx(expected, rel=1e-6), (
                f"MHD mismatch at x={x}: {mhd_val} != {expected}"
            )

    def test_hiho_threshold_shared_across_all(self):
        """Every substrate engages HIHO at exactly x=0.5."""
        from cohezion.physics.bec_bridge import BECState
        from cohezion.physics.colibre_bridge import ColibreState
        from cohezion.physics.ionic_cluster import IonicClusterState
        from cohezion.physics.lenr import LENRHamiltonian
        from cohezion.physics.mhd_plasma import MHDEquilibrium
        from cohezion.physics.toroidal_moment import FractalToroidalMoment

        assert LENRHamiltonian().reaction_threshold == pytest.approx(0.5)
        assert IonicClusterState(0.5).hiho_equilibrium() is True
        assert BECState(0.5).hiho_equilibrium() is True
        assert MHDEquilibrium(1.0).hiho_magnetized() is True
        assert FractalToroidalMoment(0.5).hiho_toroidal() is True
        assert ColibreState(0.0, 0.0, 0.5).hiho_engaged() is True

    def test_fractal_dimension_of_hiho_quality_series(self):
        """At HIHO equilibrium, toroidal FD = 1.5 = Brownian motion (same as quality series target)."""
        from cohezion.physics.toroidal_moment import FractalToroidalMoment

        t = FractalToroidalMoment(coherence=0.5)
        assert t.fractal_dimension() == pytest.approx(1.5, rel=1e-6)
