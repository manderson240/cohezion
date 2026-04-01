"""Tests for M24 physics wiring — Hamiltonian, Triune, Phonons endpoints.

Verifies that each module is correctly exposed via the Genesis Engine API
and produces valid responses with expected shapes and ranges.
"""

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from cohezion.api import app


client = TestClient(app)


# ─── Hamiltonian Wiring ──────────────────────────────────────────


class TestHamiltonianWiring:
    """Verify Hamiltonian dynamics API endpoint."""

    def test_simulate_default_returns_200(self):
        resp = client.get("/api/physics/hamiltonian/simulate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["potential"] == "double_well"
        assert data["epochs"] == 50

    def test_simulate_returns_energy_values(self):
        resp = client.get("/api/physics/hamiltonian/simulate")
        data = resp.json()
        assert isinstance(data["initial_energy"], float)
        assert isinstance(data["final_energy"], float)
        assert data["trajectory_checkpoints"] > 0

    def test_simulate_harmonic_potential(self):
        resp = client.get("/api/physics/hamiltonian/simulate?potential=harmonic&epochs=20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["potential"] == "harmonic"
        assert data["epochs"] == 20

    def test_simulate_clamps_epochs(self):
        resp = client.get("/api/physics/hamiltonian/simulate?epochs=9999")
        data = resp.json()
        assert data["epochs"] <= 500

    def test_direct_hamiltonian_dynamics(self):
        """Verify the module works directly (not just through API)."""
        from cohezion.physics.hamiltonian import HamiltonianDynamics

        dyn = HamiltonianDynamics(dt=0.01, temperature=0.01)
        z0 = np.random.default_rng(0).normal(0.5, 0.1, (2, 4)).astype(np.float32)
        z_final = dyn.simulate(z0, epochs=10, seed=0)
        assert z_final.shape == z0.shape
        assert z_final.dtype == np.float32


# ─── Triune Manifold Wiring ──────────────────────────────────────


class TestTriuneWiring:
    """Verify Triune manifold state API endpoint."""

    def test_triune_state_returns_200(self):
        resp = client.get("/api/physics/triune/state")
        assert resp.status_code == 200

    def test_triune_state_has_correct_dimensions(self):
        resp = client.get("/api/physics/triune/state")
        data = resp.json()
        assert len(data["doer"]) == 12
        assert len(data["thinker"]) == 512
        assert len(data["knower"]) == 2048

    def test_triune_coherence_in_valid_range(self):
        resp = client.get("/api/physics/triune/state")
        data = resp.json()
        assert 0.0 <= data["hiho_coherence"] <= 1.0

    def test_triune_restoring_force_present(self):
        resp = client.get("/api/physics/triune/state")
        data = resp.json()
        assert isinstance(data["restoring_force"], float)

    def test_direct_triune_state_validation(self):
        """Verify Pydantic validation catches wrong dimensions."""
        from cohezion.universe.triune_manifold import TriuneState

        with pytest.raises(Exception):
            TriuneState(
                doer=torch.zeros(5),  # Wrong: should be 12
                thinker=torch.zeros(512),
                knower=torch.zeros(2048),
            )


# ─── Spatial Phonons Wiring ──────────────────────────────────────


class TestPhononsWiring:
    """Verify spatial phonons API endpoint."""

    def test_phonon_state_returns_200(self):
        resp = client.get("/api/physics/phonons/state")
        assert resp.status_code == 200

    def test_phonon_state_has_expansion_metrics(self):
        resp = client.get("/api/physics/phonons/state")
        data = resp.json()
        assert "expansion_rate" in data
        assert "viscous_drag" in data
        assert "coherence_gain" in data

    def test_phonon_state_before_after_differ(self):
        resp = client.get("/api/physics/phonons/state")
        data = resp.json()
        # Temporal dimension should advance by delta_t
        assert data["state_after"]["temporal"] > data["state_before"]["temporal"]

    def test_phonon_custom_parameters(self):
        resp = client.get("/api/physics/phonons/state?viscosity=0.1&coupling=0.2")
        assert resp.status_code == 200

    def test_direct_phonon_engine(self):
        """Verify the module works directly."""
        from cohezion.universe.engine import AxiomaticState
        from cohezion.universe.spatial_phonons import SpatialPhononsEngine

        engine = SpatialPhononsEngine()
        state = AxiomaticState()
        new_state = engine.evolve_state(state, delta_t=0.1)
        assert new_state.temporal == pytest.approx(state.temporal + 0.1)
