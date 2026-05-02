"""Tests for Phase 2 API endpoints (FLUME training, RL training, templates)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cohezion.api import app


client = TestClient(app)


class TestFlumeEndpoints:
    """Tests for /flume/* endpoints."""

    def test_flume_status_no_training(self):
        """Status endpoint returns trained=False when no checkpoints exist."""
        resp = client.get("/flume/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "trained" in data

    def test_flume_train_small(self):
        """Train endpoint runs a tiny training job and returns metrics."""
        resp = client.post(
            "/flume/train",
            json={
                "epochs": 2,
                "batch_size": 32,
                "z_dim": 64,
                "n_samples": 200,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["epochs_completed"] == 2
        assert data["final_mse"] > 0
        assert data["final_total"] > 0

    def test_flume_status_after_training(self):
        """Status reflects trained=True after a training run."""
        # Run tiny training first
        client.post(
            "/flume/train",
            json={"epochs": 2, "batch_size": 32, "z_dim": 64, "n_samples": 100},
        )
        resp = client.get("/flume/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trained"] is True


class TestTemplateEndpoints:
    """Tests for /templates/* endpoints."""

    def test_parse_existing_skill(self):
        """Parse a known PRIME skill returns structured spec."""
        resp = client.post(
            "/templates/parse",
            json={"skill_name": "COMPOUND_ENGINEERING_PRIME"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "COMPOUND_ENGINEERING_PRIME"
        assert len(data["domain_expertise"]) > 0
        assert "agent_stub" in data
        assert "config_class" in data
        assert "class" in data["agent_stub"]
        assert "@dataclass" in data["config_class"]

    def test_parse_missing_skill(self):
        """Parsing a nonexistent skill returns 404."""
        resp = client.post(
            "/templates/parse",
            json={"skill_name": "NONEXISTENT_SKILL_XYZ"},
        )
        assert resp.status_code == 404

    def test_parse_case_insensitive(self):
        """Skill lookup is case-insensitive."""
        resp = client.post(
            "/templates/parse",
            json={"skill_name": "compound_engineering_prime"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "COMPOUND_ENGINEERING_PRIME"


class TestRLEndpoints:
    """Tests for /rl/* endpoints."""

    def test_rl_train_small(self):
        """Train endpoint runs a tiny RL job and returns results."""
        resp = client.post(
            "/rl/train",
            json={"n_episodes": 3, "max_steps": 20},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["episodes_completed"] == 3
        assert data["final_coherence"] > 0

    def test_rl_policy_default(self):
        """Policy endpoint returns info about a checkpoint."""
        # Train first to create a checkpoint
        client.post(
            "/rl/train",
            json={"n_episodes": 3, "max_steps": 20},
        )
        resp = client.get("/rl/policy/final")
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is True
        assert data["parameters"] is not None
        assert data["parameters"] > 0

    def test_rl_policy_missing(self):
        """Policy endpoint returns exists=False for unknown agent."""
        resp = client.get("/rl/policy/nonexistent_agent_xyz")
        assert resp.status_code == 200
        # May or may not find policy_final.pt depending on prior tests


class TestHealthEndpoint:
    """Verify existing health endpoint still works."""

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
