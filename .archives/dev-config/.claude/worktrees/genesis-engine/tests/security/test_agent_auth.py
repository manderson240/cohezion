"""Tests for per-agent authentication (Task #1: Phase 2 Security)."""

from datetime import UTC, datetime, timedelta

import pytest

from cohezion.security.agent_auth import AgentAuthManager, AgentCredential


@pytest.fixture
def auth_manager():
    """Create test auth manager (no vault persistence)."""
    return AgentAuthManager(enable_vault_persistence=False)


@pytest.fixture
def credentials_dir(tmp_path):
    """Create temporary vault directory."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    return vault_dir


class TestAgentCredentialModel:
    """Tests for AgentCredential dataclass."""

    def test_credential_creation(self):
        """Test creating new credential."""
        cred = AgentCredential(
            agent_id="agent-1",
            token="token-abc123",
            permissions=["read", "write"],
            is_active=True,
        )

        assert cred.agent_id == "agent-1"
        assert cred.token == "token-abc123"
        assert cred.permissions == ["read", "write"]
        assert cred.is_active is True

    def test_credential_expiration(self):
        """Test credential expiration check."""
        now = datetime.now(UTC)

        # Not expired
        cred = AgentCredential(
            agent_id="agent-1",
            token="token-1",
            expires_at=now + timedelta(days=1),
        )
        assert not cred.is_expired()

        # Expired
        expired_cred = AgentCredential(
            agent_id="agent-2",
            token="token-2",
            expires_at=now - timedelta(days=1),
        )
        assert expired_cred.is_expired()

    def test_credential_permission_check(self):
        """Test permission validation."""
        cred = AgentCredential(
            agent_id="agent-1",
            token="token-1",
            permissions=["read", "write"],
        )

        assert cred.has_permission("read")
        assert cred.has_permission("write")
        assert not cred.has_permission("delete")

    def test_credential_to_dict(self):
        """Test credential serialization."""
        cred = AgentCredential(
            agent_id="agent-1",
            token="token-1",
            permissions=["read"],
            is_active=True,
        )

        data = cred.to_dict()
        assert data["agent_id"] == "agent-1"
        assert data["token"] == "token-1"
        assert data["permissions"] == ["read"]
        assert data["is_active"] is True


class TestAgentAuthManagerBasics:
    """Tests for basic AuthManager functionality."""

    def test_create_credential(self, auth_manager):
        """Test creating new agent credential."""
        cred = auth_manager.create_agent_credential(
            agent_id="agent-1",
            permissions=["read", "write"],
        )

        assert cred.agent_id == "agent-1"
        assert len(cred.token) > 0
        assert cred.is_active is True
        assert "read" in cred.permissions
        assert "write" in cred.permissions

    def test_token_validation(self, auth_manager):
        """Test token validation."""
        cred = auth_manager.create_agent_credential("agent-1", ["read"])

        # Should validate successfully
        result = auth_manager.validate_token(cred.token)
        assert result is not None
        assert result.agent_id == "agent-1"
        assert result.is_active

    def test_invalid_token(self, auth_manager):
        """Test invalid token returns None."""
        result = auth_manager.validate_token("invalid-token-xyz")
        assert result is None

    def test_empty_token(self, auth_manager):
        """Test empty token returns None."""
        result = auth_manager.validate_token("")
        assert result is None

    def test_default_permissions(self, auth_manager):
        """Test default permissions."""
        cred = auth_manager.create_agent_credential("agent-1")

        # Should default to read/write
        assert "read" in cred.permissions
        assert "write" in cred.permissions

    def test_token_uniqueness(self, auth_manager):
        """Test tokens are unique."""
        cred1 = auth_manager.create_agent_credential("agent-1")
        cred2 = auth_manager.create_agent_credential("agent-2")

        assert cred1.token != cred2.token


class TestTokenExpiration:
    """Tests for token expiration."""

    def test_expired_token_validation(self, auth_manager):
        """Test expired tokens are rejected."""
        # Create credential with past expiration
        now = datetime.now(UTC)
        cred = AgentCredential(
            agent_id="agent-1",
            token="token-1",
            expires_at=now - timedelta(days=1),  # Already expired
            is_active=True,
        )
        auth_manager.token_cache["token-1"] = cred

        # Should reject expired token
        result = auth_manager.validate_token("token-1")
        assert result is None

    def test_not_yet_expired_token(self, auth_manager):
        """Test token expiring soon is still valid."""
        now = datetime.now(UTC)
        cred = AgentCredential(
            agent_id="agent-1",
            token="token-1",
            expires_at=now + timedelta(hours=1),
            is_active=True,
        )
        auth_manager.token_cache["token-1"] = cred

        # Should accept
        result = auth_manager.validate_token("token-1")
        assert result is not None


class TestCredentialRevocation:
    """Tests for credential revocation."""

    def test_revoke_credential(self, auth_manager):
        """Test revoking agent's credential."""
        cred = auth_manager.create_agent_credential("agent-1")
        token = cred.token

        # Should be valid before revocation
        assert auth_manager.validate_token(token) is not None

        # Revoke
        result = auth_manager.revoke_credential("agent-1")
        assert result is True

        # Should be invalid after revocation
        assert auth_manager.validate_token(token) is None

    def test_revoke_nonexistent_agent(self, auth_manager):
        """Test revoking nonexistent agent."""
        result = auth_manager.revoke_credential("nonexistent-agent")
        assert result is False

    def test_revoked_credential_inactive(self, auth_manager):
        """Test revoked credential is marked inactive."""
        cred = auth_manager.create_agent_credential("agent-1")
        token = cred.token

        auth_manager.revoke_credential("agent-1")

        # Check that credential is marked inactive
        credential = auth_manager.token_cache[token]
        assert credential.is_active is False


class TestCredentialRotation:
    """Tests for credential rotation."""

    def test_rotate_credential(self, auth_manager):
        """Test rotating agent's credential."""
        old_cred = auth_manager.create_agent_credential("agent-1", ["read", "write"])
        old_token = old_cred.token

        # Rotate
        new_cred = auth_manager.rotate_credentials("agent-1")

        assert new_cred is not None
        assert new_cred.token != old_token
        assert new_cred.agent_id == "agent-1"

        # Old token should be invalid
        assert auth_manager.validate_token(old_token) is None

        # New token should be valid
        assert auth_manager.validate_token(new_cred.token) is not None

    def test_rotate_preserves_permissions(self, auth_manager):
        """Test rotation preserves permissions by default."""
        auth_manager.create_agent_credential("agent-1", ["read", "execute"])

        rotated = auth_manager.rotate_credentials("agent-1")

        assert set(rotated.permissions) == {"read", "execute"}

    def test_rotate_with_new_permissions(self, auth_manager):
        """Test rotating with new permissions."""
        auth_manager.create_agent_credential("agent-1", ["read"])

        rotated = auth_manager.rotate_credentials("agent-1", ["write", "delete"])

        assert set(rotated.permissions) == {"write", "delete"}

    def test_rotate_nonexistent_agent(self, auth_manager):
        """Test rotating nonexistent agent."""
        result = auth_manager.rotate_credentials("nonexistent")
        assert result is None


class TestGetCredentialByAgentId:
    """Tests for credential lookup by agent ID."""

    def test_get_credential_by_agent_id(self, auth_manager):
        """Test retrieving credential by agent ID."""
        cred = auth_manager.create_agent_credential("agent-1")

        result = auth_manager.get_credential_by_agent_id("agent-1")
        assert result is not None
        assert result.token == cred.token

    def test_get_nonexistent_agent(self, auth_manager):
        """Test retrieving nonexistent agent."""
        result = auth_manager.get_credential_by_agent_id("nonexistent")
        assert result is None

    def test_get_revoked_agent(self, auth_manager):
        """Test retrieving revoked agent returns None."""
        auth_manager.create_agent_credential("agent-1")
        auth_manager.revoke_credential("agent-1")

        result = auth_manager.get_credential_by_agent_id("agent-1")
        assert result is None


class TestMultipleAgents:
    """Tests with multiple agents."""

    def test_multiple_agents(self, auth_manager):
        """Test managing multiple agents."""
        cred1 = auth_manager.create_agent_credential("agent-1")
        cred2 = auth_manager.create_agent_credential("agent-2")
        cred3 = auth_manager.create_agent_credential("agent-3")

        # All should be valid
        assert auth_manager.validate_token(cred1.token) is not None
        assert auth_manager.validate_token(cred2.token) is not None
        assert auth_manager.validate_token(cred3.token) is not None

        # Revoking one shouldn't affect others
        auth_manager.revoke_credential("agent-1")
        assert auth_manager.validate_token(cred1.token) is None
        assert auth_manager.validate_token(cred2.token) is not None
        assert auth_manager.validate_token(cred3.token) is not None

    def test_stats(self, auth_manager):
        """Test getting auth statistics."""
        auth_manager.create_agent_credential("agent-1")
        auth_manager.create_agent_credential("agent-2")
        auth_manager.create_agent_credential("agent-3")

        stats = auth_manager.get_stats()

        assert stats["total_credentials"] == 3
        assert stats["active_credentials"] == 3
        assert stats["agents"] == 3


class TestCleanupExpiredCredentials:
    """Tests for expired credential cleanup."""

    def test_cleanup_expired(self, auth_manager):
        """Test cleaning up expired credentials."""
        now = datetime.now(UTC)

        # Create expired credential
        expired = AgentCredential(
            agent_id="expired-agent",
            token="expired-token",
            expires_at=now - timedelta(days=1),
            is_active=True,
        )
        auth_manager.token_cache["expired-token"] = expired

        # Create active credential
        active = auth_manager.create_agent_credential("active-agent")

        assert len(auth_manager.token_cache) == 2

        # Cleanup
        deleted = auth_manager.cleanup_expired_credentials()

        assert deleted == 1
        assert len(auth_manager.token_cache) == 1
        assert auth_manager.validate_token(active.token) is not None
        assert auth_manager.validate_token("expired-token") is None
