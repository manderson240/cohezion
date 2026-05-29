"""Tests for COLIBRE/SWIFT cosmological simulation bridge."""

from __future__ import annotations

import pytest

from cohezion.physics.colibre_bridge import AgentAsEVO, ColibreState


class TestColibreState:
    def test_hiho_engaged_at_half_hot_fraction(self):
        s = ColibreState(ism_hot_fraction=0.5)
        assert s.hiho_engaged() is True

    def test_hiho_not_engaged_at_extremes(self):
        assert ColibreState(ism_hot_fraction=0.0).hiho_engaged() is False
        assert ColibreState(ism_hot_fraction=1.0).hiho_engaged() is False

    def test_colibre_coherence_peaks_at_half(self):
        s = ColibreState(ism_hot_fraction=0.5)
        assert abs(s.colibre_coherence - 1.0) < 1e-6

    def test_colibre_coherence_vanishes_at_extremes(self):
        assert ColibreState(ism_hot_fraction=0.0).colibre_coherence == pytest.approx(0.0)
        assert ColibreState(ism_hot_fraction=1.0).colibre_coherence == pytest.approx(0.0)

    def test_colibre_matches_lenr_kernel(self):
        """COLIBRE coherence uses SAME 4x(1-x) formula as LENR."""
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        for f in [0.2, 0.3, 0.5, 0.7, 0.9]:
            s = ColibreState(ism_hot_fraction=f)
            lenr_rate = h.reaction_rate(f)
            # They use the same kernel — COLIBRE coherence = normalized LENR rate
            assert s.colibre_coherence == pytest.approx(lenr_rate, rel=1e-6), (
                f"COLIBRE coherence {s.colibre_coherence:.4f} != LENR rate {lenr_rate:.4f} at f={f}"
            )

    def test_sfr_as_lenr_rate_peaks_at_hiho(self):
        s = ColibreState(ism_hot_fraction=0.5, sfr_density=0.02)
        rate = s.sfr_as_lenr_rate()
        assert rate == pytest.approx(1.0, rel=1e-6)

    def test_sfr_as_lenr_rate_vanishes_at_extremes(self):
        assert ColibreState(ism_hot_fraction=0.0).sfr_as_lenr_rate() == pytest.approx(0.0)
        assert ColibreState(ism_hot_fraction=1.0).sfr_as_lenr_rate() == pytest.approx(0.0)

    def test_to_ionic_cluster_mapping(self):
        s = ColibreState(ism_hot_fraction=0.48)
        cluster = s.to_ionic_cluster()
        assert cluster.plasma_density == pytest.approx(0.48, abs=1e-9)
        assert cluster.hiho_equilibrium() is True

    def test_autonomy_event_format(self):
        s = ColibreState(redshift=2.0, ism_hot_fraction=0.5)
        event = s.to_autonomy_event()
        assert event["source"] == "colibre"
        assert "coherence" in event
        assert "redshift" in event

    def test_cosmic_time_at_present(self):
        s = ColibreState(redshift=0.0)
        age = s.cosmic_time_gyr
        assert 13.0 < age <= 14.0  # ~13.8 Gyr

    def test_clamps_hot_fraction(self):
        s = ColibreState(ism_hot_fraction=1.5)
        assert s.ism_hot_fraction <= 1.0
        s_neg = ColibreState(ism_hot_fraction=-0.1)
        assert s_neg.ism_hot_fraction >= 0.0

    def test_hiho_same_threshold_as_lenr_and_ionic(self):
        """All stealthskater substrates + COLIBRE share the same HIHO threshold."""
        from cohezion.physics.ionic_cluster import IonicClusterState
        from cohezion.physics.lenr import LENRHamiltonian

        h = LENRHamiltonian()
        ic = IonicClusterState(plasma_density=h.reaction_threshold)
        s = ColibreState(ism_hot_fraction=h.reaction_threshold)

        assert h.reaction_threshold == pytest.approx(0.5)
        assert ic.hiho_equilibrium() is True
        assert s.hiho_engaged() is True


class TestAgentAsEVO:
    def test_engineer_maps_to_gas(self):
        a = AgentAsEVO("eng-1", "engineer")
        assert a.particle_type == "gas"

    def test_synthesizer_maps_to_dark_matter(self):
        a = AgentAsEVO("synth-1", "synthesizer")
        assert a.particle_type == "dark_matter"

    def test_knowledge_maps_to_star(self):
        a = AgentAsEVO("know-1", "knowledge")
        assert a.particle_type == "star"

    def test_harness_maps_to_black_hole(self):
        a = AgentAsEVO("harness-1", "harness")
        assert a.particle_type == "black_hole"

    def test_gas_can_star_form_at_hiho(self):
        a = AgentAsEVO("gas-1", "engineer")
        s = ColibreState(ism_hot_fraction=0.5, sfr_density=0.02)
        assert a.can_star_form(s) is True

    def test_gas_cannot_star_form_below_hiho(self):
        a = AgentAsEVO("gas-1", "engineer")
        s = ColibreState(ism_hot_fraction=0.1, sfr_density=0.02)
        assert a.can_star_form(s) is False

    def test_dm_cannot_star_form(self):
        a = AgentAsEVO("dm-1", "synthesizer")
        s = ColibreState(ism_hot_fraction=0.5, sfr_density=0.02)
        assert a.can_star_form(s) is False

    def test_all_agents_share_hiho_threshold(self):
        """All EVO agent types share the universal 0.5 HIHO threshold."""
        for agent_type in ["synthesizer", "engineer", "knowledge", "harness"]:
            a = AgentAsEVO(f"{agent_type}-test", agent_type)
            assert a.hiho_threshold == pytest.approx(0.5)
