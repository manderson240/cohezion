"""TDD tests for ResearchAgent API endpoints.

Phase 2: Red (Write failing tests first)
These tests will initially fail, then we'll make them pass.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

# Import the FastAPI app - this will fail initially if not set up
from cohezion.api import app


# Create test client
client = TestClient(app)


class TestResearchAPIEndpoints:
    """[P0] Comprehensive API endpoint tests."""

    def test_start_research_endpoint(self):
        """[P0] POST /research/start should create new research session."""
        # Arrange
        config = {
            "experiment_time_budget": 300.0,
            "max_experiments": 10,
            "target_metric": "val_bpb",
        }

        # Act
        response = client.post("/research/start", json=config)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "running"
        assert data["experiments_remaining"] == 10

    def test_start_multi_agent_research_endpoint(self):
        """[P0] POST /research/start-multi-agent should create multi-agent session."""
        # Arrange
        config = {
            "num_agents": 3,
            "experiments_per_agent": 5,
            "agent_diversity": "high",
        }

        # Act
        response = client.post("/research/start-multi-agent", json=config)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["experiments_remaining"] == 15  # 3 * 5

    def test_get_research_status_endpoint(self):
        """[P0] GET /research/status/{id} should return session status."""
        # First create a session
        start_response = client.post(
            "/research/start",
            json={
                "experiment_time_budget": 300.0,
                "max_experiments": 10,
            },
        )
        session_id = start_response.json()["session_id"]

        # Get status
        response = client.get(f"/research/status/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "experiments_completed" in data
        assert "best_metric" in data

    def test_get_research_results_endpoint(self):
        """[P0] GET /research/results/{id} should return detailed results."""
        # First create a session
        start_response = client.post(
            "/research/start",
            json={
                "experiment_time_budget": 300.0,
                "max_experiments": 10,
            },
        )
        session_id = start_response.json()["session_id"]

        # Get results
        response = client.get(f"/research/results/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "experiments_completed" in data
        assert "best_metric" in data
        assert "checkpoint_path" in data

    def test_stop_research_endpoint(self):
        """[P0] POST /research/stop/{id} should stop session gracefully."""
        # First create a session
        start_response = client.post(
            "/research/start",
            json={
                "experiment_time_budget": 300.0,
                "max_experiments": 10,
            },
        )
        session_id = start_response.json()["session_id"]

        # Stop session
        response = client.post(f"/research/stop/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["session_id"] == session_id

    def test_get_experiment_log_endpoint(self):
        """[P0] GET /research/experiments/{id} should return experiment log."""
        # First create a session
        start_response = client.post(
            "/research/start",
            json={
                "experiment_time_budget": 300.0,
                "max_experiments": 10,
            },
        )
        session_id = start_response.json()["session_id"]

        # Get experiment log
        response = client.get(f"/research/experiments/{session_id}?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "experiments" in data
        assert isinstance(data["experiments"], list)

    def test_get_research_dashboard_endpoint(self):
        """[P0] GET /research/dashboard should return overview."""
        response = client.get("/research/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "active_sessions" in data
        assert "single_agent_sessions" in data
        assert "multi_agent_sessions" in data
        assert "timestamp" in data

    def test_start_research_invalid_config(self):
        """[P0] Should reject invalid configuration."""
        # Invalid: negative time budget
        config = {
            "experiment_time_budget": -100.0,
            "max_experiments": 10,
        }

        response = client.post("/research/start", json=config)

        assert response.status_code == 422  # Validation error

    def test_get_status_nonexistent_session(self):
        """[P0] Should return 404 for non-existent session."""
        response = client.get("/research/status/nonexistent-id")

        assert response.status_code == 404

    def test_stop_nonexistent_session(self):
        """[P0] Should return 404 when stopping non-existent session."""
        response = client.post("/research/stop/nonexistent-id")

        assert response.status_code == 404


class TestResearchAPIErrorHandling:
    """[P1] Error handling and edge cases."""

    def test_start_research_missing_required_fields(self):
        """[P1] Should reject requests with missing required fields."""
        # Missing experiment_time_budget
        config = {
            "max_experiments": 10,
        }

        response = client.post("/research/start", json=config)

        # Should either use defaults or reject
        assert response.status_code in [200, 422]

    def test_start_research_invalid_json(self):
        """[P1] Should handle invalid JSON gracefully."""
        response = client.post(
            "/research/start",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_get_experiments_invalid_limit(self):
        """[P1] Should handle invalid limit parameter."""
        # First create a session
        start_response = client.post(
            "/research/start",
            json={
                "experiment_time_budget": 300.0,
                "max_experiments": 10,
            },
        )
        session_id = start_response.json()["session_id"]

        # Invalid limit (negative)
        response = client.get(f"/research/experiments/{session_id}?limit=-1")

        # Should either use default or reject
        assert response.status_code in [200, 422]


class TestResearchAPIPerformance:
    """[P2] Performance and load testing."""

    def test_start_research_response_time(self):
        """[P2] Should respond within acceptable time (endpoint only, not training)."""
        import time

        from cohezion.research import ResearchAgent

        config = {
            "experiment_time_budget": 300.0,
            "max_experiments": 10,
        }

        # Mock run_session so the background task doesn't execute real training.
        # TestClient runs background tasks synchronously; without this mock the
        # test would time the full research loop (10+ seconds) rather than just
        # the endpoint response time.
        with patch.object(ResearchAgent, "run_session"):
            start = time.time()
            response = client.post("/research/start", json=config)
            elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Endpoint itself (no training) should be fast

    def test_dashboard_response_time(self):
        """[P2] Dashboard should load quickly."""
        import time

        start = time.time()
        response = client.get("/research/dashboard")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond in less than 500ms


# TDD Cycle Tracking
# -------------------
# Test: 18 tests
# Expected Initial: 0 passing (all failing - RED phase)
# After Green: 18 passing
# After Refactor: 18 passing with cleaner code
#
# Current Status: RED (Write tests first)
# Next: Run tests to confirm they fail
# Then: Implement endpoints to make them pass
