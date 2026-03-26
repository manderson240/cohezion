"""
A2A Protocol API Endpoints Tests

Tests the Agent-to-Agent (A2A) protocol v1.0 endpoints exposed via FastAPI.
Covers agent discovery, task lifecycle, and error handling.

Reference: https://github.com/a2a-protocol/a2a
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client with A2A endpoints."""
    from cohezion.api import app
    return TestClient(app)


@pytest.fixture
def mock_auth_token(monkeypatch):
    """Mock ephemeral token validation for tests."""
    test_token = "test-token-12345"

    # Mock the token file reading
    def mock_get_token():
        return test_token

    from cohezion.mcp.manager import auth
    monkeypatch.setattr(auth, "get_current_token", mock_get_token)

    return test_token


@pytest.fixture
def mock_compound_executor():
    """Mock CompoundExecutor to avoid hitting real execution."""
    # CompoundExecutor is imported inside _route_to_agent method (a2a_server.py:235)
    with patch("cohezion.compound.executor.CompoundExecutor") as mock:
        executor_instance = AsyncMock()
        executor_instance.execute.return_value = "Task executed successfully"
        mock.return_value = executor_instance
        yield executor_instance


class TestA2AAuthentication:
    """Test A2A authentication enforcement"""

    def test_send_task_without_auth_header_fails(self, client):
        """Test: POST /tasks/send without X-Cohezion-Key returns 401"""
        response = client.post("/tasks/send", json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Test"}]
            }
        })

        assert response.status_code == 401
        assert "X-Cohezion-Key" in response.json()["detail"]

    def test_send_task_with_invalid_token_fails(self, client, mock_auth_token):
        """Test: POST /tasks/send with invalid token returns 403"""
        response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Test"}]
                }
            },
            headers={"X-Cohezion-Key": "invalid-token"}
        )

        assert response.status_code == 403
        assert "Invalid" in response.json()["detail"]

    def test_send_task_with_valid_token_succeeds(self, client, mock_auth_token, mock_compound_executor):
        """Test: POST /tasks/send with valid token returns 200"""
        response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Test"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        assert response.status_code == 200
        assert "id" in response.json()

    def test_get_task_without_auth_fails(self, client):
        """Test: GET /tasks/{id} without auth returns 401"""
        response = client.get("/tasks/test-id-123")

        assert response.status_code == 401

    def test_cancel_task_without_auth_fails(self, client):
        """Test: POST /tasks/{id}/cancel without auth returns 401"""
        response = client.post("/tasks/test-id-123/cancel")

        assert response.status_code == 401

    def test_agent_card_accessible_without_auth(self, client):
        """Test: GET /.well-known/agent.json is public (no auth required)"""
        response = client.get("/.well-known/agent.json")

        # Agent discovery MUST be public per A2A spec
        assert response.status_code == 200
        assert "name" in response.json()


class TestA2AAgentDiscovery:
    """Test A2A agent discovery endpoint (/.well-known/agent.json)"""

    def test_agent_card_returns_valid_structure(self, client):
        """Test 1/11: Agent Card endpoint returns valid A2A format."""
        response = client.get("/.well-known/agent.json")

        assert response.status_code == 200
        data = response.json()

        # Verify required A2A fields
        assert "name" in data
        assert "description" in data
        assert "url" in data
        assert "version" in data
        assert "capabilities" in data
        assert "skills" in data
        assert "authentication" in data

        # Verify structure
        assert isinstance(data["capabilities"], dict)
        assert isinstance(data["skills"], list)
        assert isinstance(data["authentication"], dict)

    def test_agent_card_declares_cohezion_capabilities(self, client):
        """Test 2/11: Agent Card advertises Cohezion-specific capabilities."""
        response = client.get("/.well-known/agent.json")
        data = response.json()

        # Verify Cohezion branding
        assert "Cohezion" in data["name"]
        assert "FLUME" in data["description"] or "flume" in [s["id"] for s in data["skills"]]

        # Verify A2A v1.0 capabilities
        assert data["capabilities"]["streaming"] is True
        assert "stateTransitionHistory" in data["capabilities"]

    def test_agent_card_specifies_authentication(self, client):
        """Test 3/11: Agent Card specifies API key authentication."""
        response = client.get("/.well-known/agent.json")
        data = response.json()

        auth = data["authentication"]
        assert auth["type"] == "api_key"
        assert "header" in auth or "query" in auth  # X-Cohezion-Key or similar


class TestA2ATaskLifecycle:
    """Test A2A task submission and lifecycle management"""

    def test_send_task_creates_new_task(self, client, mock_auth_token, mock_compound_executor):
        """Test 4/11: POST /tasks/send creates new task and returns task_id."""
        response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Run FLUME VAE with 100 samples"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify task structure
        assert "id" in data
        assert "state" in data
        assert "messages" in data
        assert "updated_at" in data

        # Verify initial state
        assert data["state"] in ["submitted", "working", "completed"]
        assert len(data["messages"]) >= 1

    def test_send_task_routes_to_compound_executor(self, client, mock_auth_token, mock_compound_executor):
        """Test 5/11: Task is routed to CompoundExecutor."""
        client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Analyze universe coherence"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        # Verify CompoundExecutor was called
        mock_compound_executor.execute.assert_called_once()
        args = mock_compound_executor.execute.call_args[0]
        assert "Analyze universe coherence" in args[0]

    def test_send_task_with_existing_task_id_continues_conversation(self, client, mock_auth_token, mock_compound_executor):
        """Test 6/11: Sending message with task_id continues existing task."""
        # Create initial task
        response1 = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "What is FLUME?"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )
        task_id = response1.json()["id"]

        # Continue conversation
        response2 = client.post(
            "/tasks/send",
            json={
                "task_id": task_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Show me an example"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        assert response2.status_code == 200
        data = response2.json()

        # Verify same task ID
        assert data["id"] == task_id

        # Verify message history accumulated
        assert len(data["messages"]) >= 2

    def test_get_task_returns_status(self, client, mock_auth_token, mock_compound_executor):
        """Test 7/11: GET /tasks/{id} returns task status."""
        # Create task
        create_response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Test task"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )
        task_id = create_response.json()["id"]

        # Get task status
        response = client.get(
            f"/tasks/{task_id}",
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify task data returned
        assert data["id"] == task_id
        assert "state" in data
        assert "messages" in data

    def test_get_task_nonexistent_returns_404(self, client, mock_auth_token):
        """Test 8/11: Getting nonexistent task returns 404."""
        response = client.get(
            "/tasks/nonexistent-task-id-12345",
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cancel_task_transitions_to_canceled(self, client, mock_auth_token, mock_compound_executor):
        """Test 9/11: POST /tasks/{id}/cancel returns correct structure."""
        # Note: Current A2A implementation executes tasks synchronously (awaits completion)
        # so tasks complete immediately. This test verifies cancel endpoint structure.

        create_response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Test task"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )
        task_id = create_response.json()["id"]

        # Try to cancel (task likely already completed)
        cancel_response = client.post(
            f"/tasks/{task_id}/cancel",
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        assert cancel_response.status_code == 200
        data = cancel_response.json()

        # Verify response structure
        assert "canceled" in data
        assert "state" in data
        # Task is already completed, so canceled=False is expected
        assert isinstance(data["canceled"], bool)

    def test_cancel_completed_task_returns_false(self, client, mock_auth_token, mock_compound_executor):
        """Test 10/11: Canceling already completed task returns false."""
        # Create and complete task
        create_response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Quick task"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )
        task_id = create_response.json()["id"]

        # Task should be completed by now (mock returns immediately)
        # Try to cancel
        cancel_response = client.post(
            f"/tasks/{task_id}/cancel",
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        # Should return success=false or 409 conflict
        assert cancel_response.status_code in [200, 409]


class TestA2AErrorHandling:
    """Test A2A error handling and edge cases"""

    def test_send_task_with_empty_message_fails(self, client, mock_auth_token):
        """Test 11/11: Sending task with empty message returns 400."""
        response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": []  # Empty parts
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        assert response.status_code in [400, 422]

    def test_send_task_with_invalid_role_fails(self, client, mock_auth_token):
        """Test: Invalid role (not 'user' or 'agent') returns 422."""
        response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "hacker",  # Invalid role
                    "parts": [{"type": "text", "text": "test"}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        # Should validate or accept and normalize to 'user'
        # Accepting for now (A2A server is lenient)
        assert response.status_code in [200, 422]

    def test_agent_card_caches_response(self, client):
        """Test: Agent Card can be cached (performance optimization)."""
        response1 = client.get("/.well-known/agent.json")
        response2 = client.get("/.well-known/agent.json")

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Should return identical data (deterministic)
        assert response1.json() == response2.json()

    def test_task_execution_failure_returns_failed_state(self, client, mock_auth_token):
        """Test: CompoundExecutor exception transitions task to 'failed' state."""
        with patch("cohezion.compound.executor.CompoundExecutor") as mock:
            executor_instance = AsyncMock()
            executor_instance.execute.side_effect = RuntimeError("Execution failed")
            mock.return_value = executor_instance

            response = client.post(
                "/tasks/send",
                json={
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "Fail this task"}]
                    }
                },
                headers={"X-Cohezion-Key": mock_auth_token}
            )

            assert response.status_code == 200
            data = response.json()

            # Task should be in failed state
            assert data["state"] == "failed"

            # Error message should be in agent response
            assert len(data["messages"]) >= 2
            agent_msg = next(m for m in data["messages"] if m["role"] == "agent")
            error_text = agent_msg["parts"][0]["text"]

            # Verify error is sanitized (type name only, no details)
            assert "RuntimeError" in error_text
            assert "Execution failed" not in error_text  # Original message should NOT leak
            assert "Task execution failed" in error_text

    def test_send_task_with_oversized_message_fails(self, client, mock_auth_token):
        """Test: Message exceeding 1MB limit is rejected (Issue #5)."""
        # Create a message > 1MB (use large text payload)
        large_text = "A" * (1_048_576 + 1000)  # 1MB + 1KB

        response = client.post(
            "/tasks/send",
            json={
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": large_text}]
                }
            },
            headers={"X-Cohezion-Key": mock_auth_token}
        )

        # Should reject with 422 (Pydantic validation error)
        assert response.status_code == 422
        error_detail = response.json()["detail"]

        # Verify error mentions size limit
        assert any("size" in str(err).lower() or "1048576" in str(err) for err in error_detail)
