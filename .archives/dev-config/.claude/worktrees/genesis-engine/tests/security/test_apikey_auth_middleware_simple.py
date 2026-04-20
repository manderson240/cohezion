"""Simplified tests for APIKeyAuth middleware."""


import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from cohezion.security.agent_auth import AgentAuthManager
from cohezion.security.apikey_auth_middleware import APIKeyAuthMiddleware


@pytest.fixture
def auth_manager():
    """Create test auth manager."""
    return AgentAuthManager(enable_vault_persistence=False)


class TestMiddlewareProtection:
    """Test middleware authentication protection."""

    def test_middleware_blocks_missing_token(self, auth_manager):
        """Test middleware blocks request without token."""
        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        @app.post("/api/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.post("/api/test")

        assert response.status_code == 401
        assert "X-Agent-Token" in response.json()["detail"]

    def test_middleware_blocks_invalid_token(self, auth_manager):
        """Test middleware blocks request with invalid token."""
        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        @app.post("/api/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.post(
            "/api/test",
            headers={"X-Agent-Token": "invalid-token"},
        )

        assert response.status_code == 401

    def test_middleware_allows_valid_token(self, auth_manager):
        """Test middleware allows request with valid token."""
        cred = auth_manager.create_agent_credential("agent-1")

        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        @app.post("/api/test")
        async def test_endpoint(request: Request):
            return {"agent_id": request.state.agent_id}

        client = TestClient(app)
        response = client.post(
            "/api/test",
            headers={"X-Agent-Token": cred.token},
        )

        assert response.status_code == 200
        assert response.json()["agent_id"] == "agent-1"

    def test_middleware_skips_health_check(self, auth_manager):
        """Test middleware skips health check endpoint."""
        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_middleware_enriches_request_state(self, auth_manager):
        """Test middleware enriches request state with credential info."""
        cred = auth_manager.create_agent_credential("test-agent", ["read", "write"])

        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        @app.post("/api/test")
        async def test_endpoint(request: Request):
            return {
                "agent_id": request.state.agent_id,
                "permissions": request.state.agent_permissions,
            }

        client = TestClient(app)
        response = client.post(
            "/api/test",
            headers={"X-Agent-Token": cred.token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test-agent"
        assert set(data["permissions"]) == {"read", "write"}

    def test_middleware_revoked_token_rejected(self, auth_manager):
        """Test middleware rejects revoked credentials."""
        cred = auth_manager.create_agent_credential("agent-1")

        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        @app.post("/api/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Token works initially
        response = client.post(
            "/api/test",
            headers={"X-Agent-Token": cred.token},
        )
        assert response.status_code == 200

        # Revoke credential
        auth_manager.revoke_credential("agent-1")

        # Token now rejected
        response = client.post(
            "/api/test",
            headers={"X-Agent-Token": cred.token},
        )
        assert response.status_code == 401


class TestProtectedPaths:
    """Test custom protected path configuration."""

    def test_custom_protected_paths(self, auth_manager):
        """Test custom protected paths."""
        app = FastAPI()
        app.add_middleware(
            APIKeyAuthMiddleware,
            auth_manager=auth_manager,
            protected_paths=["/admin/"],
            skip_paths=["/public/"],
        )

        @app.get("/public/info")
        async def public_info():
            return {"public": True}

        @app.get("/admin/stats")
        async def admin_stats(request: Request):
            return {"admin": True, "agent": request.state.agent_id}

        client = TestClient(app)

        # Public endpoint doesn't require auth
        response = client.get("/public/info")
        assert response.status_code == 200

        # Admin endpoint requires auth
        response = client.get("/admin/stats")
        assert response.status_code == 401

        # Admin endpoint works with valid token
        cred = auth_manager.create_agent_credential("admin-agent")
        response = client.get(
            "/admin/stats",
            headers={"X-Agent-Token": cred.token},
        )
        assert response.status_code == 200
        assert response.json()["agent"] == "admin-agent"


class TestMultipleAgents:
    """Test multiple agent handling."""

    def test_multiple_agents_isolation(self, auth_manager):
        """Test multiple agents are isolated."""
        cred1 = auth_manager.create_agent_credential("agent-1")
        cred2 = auth_manager.create_agent_credential("agent-2")

        app = FastAPI()
        app.add_middleware(APIKeyAuthMiddleware, auth_manager=auth_manager)

        @app.post("/api/test")
        async def test_endpoint(request: Request):
            return {"agent_id": request.state.agent_id}

        client = TestClient(app)

        # Agent 1 request
        response1 = client.post(
            "/api/test",
            headers={"X-Agent-Token": cred1.token},
        )
        assert response1.json()["agent_id"] == "agent-1"

        # Agent 2 request
        response2 = client.post(
            "/api/test",
            headers={"X-Agent-Token": cred2.token},
        )
        assert response2.json()["agent_id"] == "agent-2"
