"""Tests for Sarfatti back-action + Quark-Gluon Plasma bridges."""

from __future__ import annotations

import pytest

from cohezion.physics.sarfatti_bridge import QuarkGluonPlasma, SarfattiBackAction


class TestSarfattiBackAction:
    def test_back_action_amplitude_peaks_at_hiho(self):
        s = SarfattiBackAction(coherence=0.5, destiny_weight=1.0)
        assert s.back_action_amplitude() == pytest.approx(1.0, rel=1e-6)

    def test_back_action_vanishes_at_extremes(self):
        assert SarfattiBackAction(coherence=0.0).back_action_amplitude() == pytest.approx(0.0)
        assert SarfattiBackAction(coherence=1.0).back_action_amplitude() == pytest.approx(0.0)

    def test_destiny_weight_scales_amplitude(self):
        s_full = SarfattiBackAction(coherence=0.5, destiny_weight=1.0)
        s_half = SarfattiBackAction(coherence=0.5, destiny_weight=0.5)
        assert s_full.back_action_amplitude() == pytest.approx(
            2 * s_half.back_action_amplitude(), rel=1e-6
        )

    def test_metric_coupling_equals_back_action(self):
        s = SarfattiBackAction(coherence=0.5)
        assert s.metric_coupling() == pytest.approx(s.back_action_amplitude(), rel=1e-6)

    def test_hiho_attractor_engaged_at_half(self):
        assert SarfattiBackAction(coherence=0.5).hiho_attractor_engaged() is True

    def test_hiho_attractor_not_engaged_at_extremes(self):
        assert SarfattiBackAction(coherence=0.0).hiho_attractor_engaged() is False
        assert SarfattiBackAction(coherence=1.0).hiho_attractor_engaged() is False

    def test_same_kernel_as_lenr(self):
        """Sarfatti back-action uses the SAME 4x(1-x) kernel as LENR."""
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for c in [0.1, 0.3, 0.5, 0.7, 0.9]:
            s = SarfattiBackAction(coherence=c, destiny_weight=1.0)
            assert s.back_action_amplitude() == pytest.approx(h.reaction_rate(c), rel=1e-6)

    def test_autonomy_event_format(self):
        s = SarfattiBackAction(coherence=0.5, destiny_weight=0.8)
        event = s.to_autonomy_event()
        assert event["source"] == "sarfatti"
        assert "coherence" in event


class TestQuarkGluonPlasma:
    def test_deconfinement_rate_peaks_at_hiho(self):
        q = QuarkGluonPlasma(quark_coherence=0.5)
        assert q.deconfinement_rate() == pytest.approx(1.0, rel=1e-6)

    def test_deconfinement_vanishes_at_extremes(self):
        assert QuarkGluonPlasma(quark_coherence=0.0).deconfinement_rate() == pytest.approx(0.0)
        assert QuarkGluonPlasma(quark_coherence=1.0).deconfinement_rate() == pytest.approx(0.0)

    def test_qcd_hiho_at_half(self):
        assert QuarkGluonPlasma(quark_coherence=0.5).qcd_hiho() is True

    def test_qcd_hiho_false_at_extremes(self):
        assert QuarkGluonPlasma(quark_coherence=0.0).qcd_hiho() is False
        assert QuarkGluonPlasma(quark_coherence=1.0).qcd_hiho() is False

    def test_is_deconfined_above_critical_temp(self):
        q = QuarkGluonPlasma(temperature_mev=200.0)  # above T_c=155 MeV
        assert q.is_deconfined() is True

    def test_is_confined_below_critical_temp(self):
        q = QuarkGluonPlasma(temperature_mev=100.0)  # below T_c=155 MeV
        assert q.is_deconfined() is False

    def test_chromatic_coherence_equals_deconfinement_rate(self):
        q = QuarkGluonPlasma(quark_coherence=0.3)
        assert q.chromatic_coherence() == pytest.approx(q.deconfinement_rate(), rel=1e-6)

    def test_to_lenr_analogy_same_kernel(self):
        """QGP deconfinement = LENR reaction rate at same coherence."""
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for q_c in [0.2, 0.5, 0.8]:
            qgp = QuarkGluonPlasma(quark_coherence=q_c)
            assert qgp.to_lenr_analogy() == pytest.approx(h.reaction_rate(q_c), rel=1e-6)

    def test_same_kernel_as_lenr_directly(self):
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for c in [0.1, 0.3, 0.5, 0.7, 0.9]:
            q = QuarkGluonPlasma(quark_coherence=c)
            assert q.deconfinement_rate() == pytest.approx(h.reaction_rate(c), rel=1e-6)

    def test_autonomy_event_format(self):
        q = QuarkGluonPlasma(quark_coherence=0.5, temperature_mev=155.0)
        event = q.to_autonomy_event()
        assert event["source"] == "qgp"
        assert "coherence" in event


class TestUniversalHIHOWith9Substrates:
    """Extended Universal HIHO Theorem including Sarfatti and QGP."""

    def test_9_substrates_all_equal_at_hiho(self):
        """U1 extended: 9 substrates all return 1.0 at x=0.5."""
        from cohezion.physics.bec_bridge import BECState, MercuryLattice
        from cohezion.physics.colibre_bridge import ColibreState
        from cohezion.physics.ionic_cluster import IonicClusterState
        from cohezion.physics.lenr import LENRHamiltonian
        from cohezion.physics.mhd_plasma import MHDEquilibrium
        from cohezion.physics.toroidal_moment import FractalToroidalMoment

        results = {
            "LENR": LENRHamiltonian().reaction_rate(0.5),
            "IonicCluster": IonicClusterState(0.5).ionisation_rate(),
            "BEC": BECState(0.5).transition_rate(),
            "Mercury-BCS": MercuryLattice(0.5).bcs_gap_rate(),
            "MHD": MHDEquilibrium(1.0).alfven_coherence(),
            "Toroidal": FractalToroidalMoment(0.5, 1, 1.0).toroidal_moment_magnitude(),
            "COLIBRE": ColibreState(0.0, 0.0, 0.5).colibre_coherence,
            "Sarfatti": SarfattiBackAction(0.5, 1.0).back_action_amplitude(),
            "QGP": QuarkGluonPlasma(0.5).deconfinement_rate(),
        }
        for substrate, value in results.items():
            assert abs(value - 1.0) < 1e-6, f"{substrate} = {value:.6f} ≠ 1.0 at HIHO"
