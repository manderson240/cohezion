"""Tests for M24 wiring batch 3 — Coherence, EVO, Bioelectric Bridge, ManifoldEnv toggle.

Verifies the four remaining disconnected modules are correctly wired
into the Genesis Engine API and the ManifoldEnv dynamics toggle works.
"""

import pytest
from fastapi.testclient import TestClient

from cohezion.api import app


client = TestClient(app)


# ─── Task 1: Coherence Tracker API ──────────────────────────


class TestCoherenceWiring:
    """Verify coherence tracker API endpoint."""

    def test_coherence_default_returns_200(self):
        resp = client.get("/api/modules/coherence")
        assert resp.status_code == 200

    def test_coherence_default_is_hiho_stable(self):
        resp = client.get("/api/modules/coherence")
        data = resp.json()
        assert data["coherence"] == 0.5
        assert data["hiho_stable"] is True
        assert data["hiho_delta"] == 0.0
        assert data["stability_score"] == 1.0

    def test_coherence_custom_inputs(self):
        resp = client.get("/api/modules/coherence?internal_state=0.8&external_alignment=0.2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence"] == 0.5
        assert data["hiho_stable"] is True

    def test_coherence_unstable_region(self):
        resp = client.get("/api/modules/coherence?internal_state=1.0&external_alignment=1.0")
        data = resp.json()
        assert data["coherence"] == 1.0
        assert data["hiho_stable"] is False
        assert data["hiho_delta"] == 0.5

    def test_coherence_stability_score_range(self):
        resp = client.get("/api/modules/coherence?internal_state=0.3&external_alignment=0.3")
        data = resp.json()
        assert 0.0 <= data["stability_score"] <= 1.0


# ─── Task 2: EVO Lifecycle API ───────────────────────────────


class TestEVOWiring:
    """Verify EVO lifecycle simulation API endpoint."""

    def test_evo_simulate_returns_200(self):
        resp = client.post("/api/modules/evo/simulate")
        assert resp.status_code == 200

    def test_evo_simulate_full_lifecycle(self):
        resp = client.post("/api/modules/evo/simulate?ticks=20&seed=42")
        data = resp.json()
        assert data["agent_id"] == "genesis_agent_0"
        assert data["state"] == "dissolving"  # biography captured at dissolution
        assert data["lifetime_ticks"] == 20
        assert data["binding_energy"] >= 0.0

    def test_evo_simulate_produces_witness_marks(self):
        resp = client.post("/api/modules/evo/simulate?ticks=20&seed=42")
        data = resp.json()
        assert len(data["witness_marks"]) > 0
        assert data["witness_marks"][0]["mark_type"] == "artifact"

    def test_evo_coherence_metric_valid_range(self):
        resp = client.post("/api/modules/evo/simulate?ticks=50&seed=99")
        data = resp.json()
        assert 0.0 <= data["evo_coherence_metric"] <= 1.0

    def test_evo_custom_agent_id(self):
        resp = client.post("/api/modules/evo/simulate?agent_id=custom_agent&ticks=5")
        data = resp.json()
        assert data["agent_id"] == "custom_agent"


# ─── Task 3: Bioelectric Bridge API ─────────────────────────


class TestBioelectricBridgeWiring:
    """Verify bioelectric-to-morphospace bridge API endpoint."""

    def test_bioelectric_step_returns_200(self):
        resp = client.post(
            "/api/modules/bioelectric/step",
            json={"state": [0.3] * 12},
        )
        assert resp.status_code == 200

    def test_bioelectric_step_has_signal_fields(self):
        resp = client.post(
            "/api/modules/bioelectric/step",
            json={"state": [0.3] * 12},
        )
        data = resp.json()
        assert "voltage" in data
        assert "signal_pattern" in data
        assert data["signal_pattern"] in ("homeostatic", "regenerative", "morphogenic")

    def test_bioelectric_step_returns_new_state(self):
        resp = client.post(
            "/api/modules/bioelectric/step",
            json={"state": [0.3] * 12},
        )
        data = resp.json()
        assert len(data["new_state"]) == 12
        assert all(isinstance(v, float) for v in data["new_state"])

    def test_bioelectric_step_from_hiho(self):
        """At HIHO equilibrium, signal should be homeostatic."""
        resp = client.post(
            "/api/modules/bioelectric/step",
            json={"state": [0.5] * 12},
        )
        data = resp.json()
        assert data["signal_pattern"] == "homeostatic"
        assert abs(data["voltage"]) < 0.2

    def test_bioelectric_step_confidence_valid(self):
        resp = client.post(
            "/api/modules/bioelectric/step",
            json={"state": [0.7] * 12},
        )
        data = resp.json()
        assert 0.0 <= data["action_confidence"] <= 1.0


# ─── Task 4: ManifoldEnv Hamiltonian Toggle ──────────────────


class TestManifoldEnvDynamicsToggle:
    """Verify ManifoldEnv dynamics_engine parameter."""

    def test_default_is_lagrangian(self):
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(seed=42)
        assert env.dynamics_engine == "lagrangian"
        assert env._dynamics is not None
        assert env._hamiltonian is None

    def test_hamiltonian_mode(self):
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(dynamics_engine="hamiltonian", seed=42)
        assert env.dynamics_engine == "hamiltonian"
        assert env._hamiltonian is not None

    def test_invalid_engine_raises(self):
        from cohezion.environments.manifold_env import ManifoldEnv

        with pytest.raises(ValueError, match="dynamics_engine must be one of"):
            ManifoldEnv(dynamics_engine="invalid")

    def test_lagrangian_step(self):
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(dynamics_engine="lagrangian", seed=42)
        obs, info = env.reset(seed=42)
        action = env.action_space.sample()
        obs2, reward, terminated, truncated, info2 = env.step(action)
        assert obs2.shape == (19,)
        assert isinstance(reward, float)

    def test_hamiltonian_step(self):
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(dynamics_engine="hamiltonian", seed=42)
        obs, info = env.reset(seed=42)
        action = env.action_space.sample()
        obs2, reward, terminated, truncated, info2 = env.step(action)
        assert obs2.shape == (19,)
        assert isinstance(reward, float)
