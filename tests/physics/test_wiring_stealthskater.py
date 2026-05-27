"""Tests for Stealthskater physics wiring — LENR, IonicCluster, Dielectric, Sarfatti, QGP endpoints.

Verifies that each module is correctly exposed via the Genesis Engine API
and produces valid responses with expected shapes and ranges.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cohezion.api import app


client = TestClient(app)


class TestLenrWiring:
    """Verify LENR Hamiltonian API endpoints."""

    def test_simulate_default_returns_200(self):
        resp = client.get("/api/physics/lenr/simulate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reaction_threshold"] == 0.5
        assert data["lattice_coupling"] == 1.0
        assert data["coherence"] == 0.5
        assert data["reaction_rate"] == 1.0

    def test_simulate_custom_parameters(self):
        resp = client.get(
            "/api/physics/lenr/simulate?coherence=0.25&reaction_threshold=0.5&lattice_coupling=2.0"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reaction_threshold"] == 0.5
        assert data["lattice_coupling"] == 2.0
        assert data["coherence"] == 0.25
        # rate = 2.0 * 4 * 0.25 * (1 - 0.25) = 2.0 * 4 * 0.25 * 0.75 = 1.5
        assert data["reaction_rate"] == pytest.approx(1.5)

    def test_post_event_records_and_updates_state(self):
        # Trigger an event
        payload = {"coherence": 0.5, "agent_id": "test-lenr-agent"}
        resp = client.post("/api/physics/lenr/event", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence"] == 0.5
        assert data["reaction_rate"] == 1.0
        assert data["event_count"] == 1
        assert data["mean_rate"] == 1.0
        assert data["agent_id"] == "test-lenr-agent"

        # Trigger second event
        payload = {"coherence": 0.0, "agent_id": "test-lenr-agent"}
        resp = client.post("/api/physics/lenr/event", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence"] == 0.0
        assert data["reaction_rate"] == 0.0
        assert data["event_count"] == 2
        assert data["mean_rate"] == 0.5


class TestIonicClusterWiring:
    """Verify Ionic Cluster API endpoints."""

    def test_status_default_returns_200(self):
        resp = client.get("/api/physics/ionic-cluster/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plasma_density"] == 0.5
        assert data["cluster_size"] == 100
        assert data["hiho_tolerance"] == 0.05
        assert data["hiho_equilibrium"] is True
        assert data["ionisation_rate"] == 1.0
        assert data["active_ions"] == 50
        assert data["steps_taken"] == 0

    def test_status_custom_equilibrium(self):
        resp = client.get(
            "/api/physics/ionic-cluster/status?agent_id=test-ionic-agent&plasma_density=0.55&hiho_tolerance=0.05"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hiho_equilibrium"] is True

        resp2 = client.get(
            "/api/physics/ionic-cluster/status?agent_id=test-ionic-agent2&plasma_density=0.6&hiho_tolerance=0.05"
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["hiho_equilibrium"] is False

    def test_post_step_updates_density(self):
        agent_id = "test-step-agent"
        # First status to initialize
        client.get(f"/api/physics/ionic-cluster/status?agent_id={agent_id}&plasma_density=0.4")

        # Step by +0.1
        payload = {"delta": 0.1, "agent_id": agent_id}
        resp = client.post("/api/physics/ionic-cluster/step", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["previous_density"] == pytest.approx(0.4)
        assert data["plasma_density"] == pytest.approx(0.5)
        assert data["hiho_equilibrium"] is True
        assert data["steps_taken"] == 1


class TestDielectricWiring:
    """Verify Dielectric force and polarization API endpoints."""

    def test_polarization_default_returns_200(self):
        resp = client.get("/api/physics/dielectric/polarization")
        assert resp.status_code == 200
        data = resp.json()
        assert data["voltage"] == 10000.0
        assert data["electrode_separation"] == 0.01
        assert data["permittivity_diagonal"] == [1.0, 1.0, 1.0]
        assert data["mean_permittivity"] == 1.0
        assert len(data["biefield_brown_force"]) == 3
        # gauge connection potential should have U(1) generator LZ populated
        # LZ is index 2, diagonal elements should be diagonal permittivity - 1.0
        # Since it is vacuum [1.0, 1.0, 1.0], all values should be 0.0
        potential = data["gauge_connection_potential"]
        assert potential == [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

    def test_polarization_custom_anisotropy(self):
        resp = client.get(
            "/api/physics/dielectric/polarization?voltage=20000&electrode_separation=0.02&permittivity_diagonal=1.5,2.0,2.5"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["voltage"] == 20000.0
        assert data["electrode_separation"] == 0.02
        assert data["permittivity_diagonal"] == [1.5, 2.0, 2.5]
        assert data["mean_permittivity"] == 2.0
        potential = data["gauge_connection_potential"]
        # LZ row is index 2: [1.5-1, 2.0-1, 2.5-1] = [0.5, 1.0, 1.5]
        assert potential[2] == [0.5, 1.0, 1.5]


class TestSarfattiWiring:
    """Verify Sarfatti retrocausal back-action API endpoints."""

    def test_backaction_default_returns_200(self):
        resp = client.get("/api/physics/sarfatti/backaction")
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence"] == 0.5
        assert data["destiny_weight"] == 0.5
        assert data["back_action_amplitude"] == pytest.approx(0.5)
        assert data["metric_coupling"] == pytest.approx(0.5)
        assert data["hiho_attractor_engaged"] is True

    def test_backaction_custom(self):
        resp = client.get("/api/physics/sarfatti/backaction?coherence=0.2&destiny_weight=0.8")
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence"] == 0.2
        assert data["destiny_weight"] == 0.8
        # amplitude = 0.8 * 4 * 0.2 * 0.8 = 0.512
        assert data["back_action_amplitude"] == pytest.approx(0.512)
        assert data["hiho_attractor_engaged"] is False


class TestQuarkGluonPlasmaWiring:
    """Verify Quark-Gluon Plasma API endpoints."""

    def test_qgp_status_default_returns_200(self):
        resp = client.get("/api/physics/qgp/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["quark_coherence"] == 0.5
        assert data["temperature_mev"] == 155.0
        assert data["deconfinement_rate"] == 1.0
        assert data["qcd_hiho"] is True
        assert data["is_deconfined"] is False
        assert data["chromatic_coherence"] == 1.0
        assert data["lenr_analogy_rate"] == 1.0

    def test_qgp_status_deconfined(self):
        resp = client.get("/api/physics/qgp/status?quark_coherence=0.8&temperature_mev=200.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["quark_coherence"] == 0.8
        assert data["temperature_mev"] == 200.0
        assert data["is_deconfined"] is True
        assert data["qcd_hiho"] is False
