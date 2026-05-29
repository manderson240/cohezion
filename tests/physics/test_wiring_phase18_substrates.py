"""Tests for Phase-18 substrate wiring — BEC, Mercury, COLIBRE, MHD, Bismuth, Toroidal, TensorMetric endpoints.

Verifies that each previously-orphaned Phase-18 physics module is now exposed
via the extended Genesis Engine API and produces valid responses with the
expected HIHO kernel behaviour (4x(1-x) peaks at the 0.5 midpoint).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cohezion.api import app


client = TestClient(app)


class TestBECWiring:
    """Verify Bose-Einstein condensate endpoint."""

    def test_bec_status_default_returns_200(self):
        resp = client.get("/api/physics/bec/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["condensate_fraction"] == 0.5
        # 4 * 0.5 * 0.5 = 1.0 (HIHO peak)
        assert data["transition_rate"] == 1.0
        assert data["hiho_equilibrium"] is True
        assert data["condensed_atoms"] == 50_000
        assert data["thermal_atoms"] == 50_000

    def test_bec_transition_rate_vanishes_at_extremes(self):
        for frac in (0.0, 1.0):
            resp = client.get(f"/api/physics/bec/status?condensate_fraction={frac}")
            assert resp.status_code == 200
            assert resp.json()["transition_rate"] == 0.0


class TestMercuryWiring:
    """Verify Mercury BCS lattice endpoint."""

    def test_mercury_status_default_returns_200(self):
        resp = client.get("/api/physics/mercury/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence"] == 0.5
        assert data["lattice_coupling"] == 1.0
        # 1.0 * 4 * 0.5 * 0.5 = 1.0
        assert data["bcs_gap_rate"] == 1.0
        assert data["is_superconducting"] is True

    def test_mercury_coupling_scales_gap_rate(self):
        resp = client.get("/api/physics/mercury/status?coherence=0.5&lattice_coupling=2.0")
        assert resp.status_code == 200
        assert resp.json()["bcs_gap_rate"] == pytest.approx(2.0)


class TestColibreWiring:
    """Verify COLIBRE cosmic ISM + agent-as-EVO endpoint."""

    def test_colibre_status_default_returns_200(self):
        resp = client.get("/api/physics/colibre/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ism_hot_fraction"] == 0.5
        # 4 * 0.5 * 0.5 = 1.0 (HIHO peak)
        assert data["colibre_coherence"] == 1.0
        assert data["hiho_engaged"] is True

    def test_colibre_engineer_agent_star_forms_at_hiho(self):
        resp = client.get(
            "/api/physics/colibre/status?redshift=2.0&ism_hot_fraction=0.5&sfr_density=0.02&agent_type=engineer"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_particle_type"] == "gas"
        assert data["agent_can_star_form"] is True
        assert data["cosmic_time_gyr"] > 0.0

    def test_colibre_harness_agent_is_black_hole(self):
        resp = client.get("/api/physics/colibre/status?agent_type=harness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_particle_type"] == "black_hole"
        # black holes (harness) do not star-form
        assert data["agent_can_star_form"] is False


class TestMHDWiring:
    """Verify magnetohydrodynamic plasma endpoint."""

    def test_mhd_status_equipartition_returns_200(self):
        # plasma_beta=1.0 normalises to 0.5 → HIHO peak
        resp = client.get("/api/physics/mhd/status?plasma_beta=1.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plasma_beta"] == 1.0
        assert data["alfven_coherence"] == 1.0
        assert data["hiho_magnetized"] is True

    def test_mhd_low_beta_is_alfvenic(self):
        resp = client.get("/api/physics/mhd/status?plasma_beta=0.2&lundquist_number=1e6")
        assert resp.status_code == 200
        assert resp.json()["is_alfvenic"] is True


class TestBismuthWiring:
    """Verify bismuth diamagnetic levitation endpoint."""

    def test_bismuth_status_default_returns_200(self):
        resp = client.get("/api/physics/bismuth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["levitation_threshold_tesla"] > 0.0
        assert 0.0 <= data["diamagnetic_coherence"] <= 1.0


class TestToroidalWiring:
    """Verify fractal toroidal moment endpoint."""

    def test_toroidal_status_default_returns_200(self):
        resp = client.get("/api/physics/toroidal/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence"] == 0.5
        assert data["ring_count"] == 7
        # FD peaks at 1.5 at HIHO
        assert data["fractal_dimension"] == pytest.approx(1.5)
        assert data["time_reversal_broken"] is True
        assert data["hiho_toroidal"] is True

    def test_toroidal_moment_vanishes_at_extreme_coherence(self):
        resp = client.get("/api/physics/toroidal/status?coherence=1.0")
        assert resp.status_code == 200
        assert resp.json()["toroidal_moment_magnitude"] == pytest.approx(0.0)


class TestTensorMetricWiring:
    """Verify Sarfatti ZPF tensor-metric engineering endpoint."""

    def test_tensor_metric_hiho_perturbs_metric(self):
        resp = client.get(
            "/api/physics/tensor-metric/status?sarfatti_coherence=0.5&destiny_weight=1.0&epsilon=0.01"
        )
        assert resp.status_code == 200
        data = resp.json()
        # back_action = 1.0 * 4 * 0.5 * 0.5 = 1.0 (HIHO peak)
        assert data["back_action_amplitude"] == 1.0
        # det(g) deviates from flat Minkowski (-1.0) when ZPF active
        assert data["metric_determinant"] != pytest.approx(-1.0)
        assert data["is_flat"] is False

    def test_tensor_metric_flat_at_zero_coherence(self):
        resp = client.get("/api/physics/tensor-metric/status?sarfatti_coherence=0.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["back_action_amplitude"] == 0.0
        assert data["metric_determinant"] == pytest.approx(-1.0)
        assert data["is_flat"] is True
