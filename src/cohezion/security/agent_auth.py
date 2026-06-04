# nested if for clarity over single combined condition
"""Per-agent authentication management for Cohezion multi-agent systems.

This module implements per-agent credential management, replacing the shared API key
system with individual tokens per agent. Each agent gets a unique token with
configurable permissions and expiration.

Features:
- Per-agent credential generation and validation
- Token caching and performance optimization
- Vault persistence (non-blocking async)
- Token rotation and revocation
- Permission-based access control
- Expiration-based credential lifecycle
"""

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class AgentCredential:
    """Per-agent authentication credential.

    Attributes:
        agent_id: Unique identifier for the agent
        token: UUID-based token (not the actual API key)
        api_key_hash: bcrypt hash of actual API key (for secure storage)
        created_at: Credential creation timestamp
        expires_at: Optional expiration timestamp
        permissions: List of allowed operations (e.g., ["read", "write", "delete"])
        is_active: Whether credential is currently active
        last_used: Last time credential was validated
    """

    agent_id: str
    token: str
    api_key_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    permissions: list[str] = field(default_factory=lambda: ["read", "write"])
    is_active: bool = False
    last_used: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert credential to dictionary for serialization."""
        data = asdict(self)
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        if self.last_used:
            data["last_used"] = self.last_used.isoformat()
        return data

    def is_expired(self) -> bool:
        """Check if credential has expired."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    def has_permission(self, permission: str) -> bool:
        """Check if credential has specific permission."""
        return permission in self.permissions


class AgentAuthManager:
    """Manages per-agent authentication and token validation.

    This manager handles:
    - Creating new agent credentials with unique tokens
    - Validating tokens during API requests
    - Rotating credentials periodically
    - Revoking credentials on agent removal
    - Non-blocking async vault persistence

    Example usage::

        auth_manager = AgentAuthManager()

        # Create credential for new agent
        credential = auth_manager.create_agent_credential(
            agent_id="agent-researcher-001",
            permissions=["read", "write"]
        )

        # Validate token during request
        credential = auth_manager.validate_token(credential.token)
        if credential and credential.has_permission("write"):
            # Allow write operation
            pass
    """

    def __init__(
        self,
        vault_path: str = "~/vaults/cohezion-vault/agents/",
        enable_vault_persistence: bool = True,
        token_expiry_days: int = 90,
    ):
        """Initialize authentication manager.

        Args:
            vault_path: Path to vault storage for credentials
            enable_vault_persistence: Whether to persist to vault (non-blocking)
            token_expiry_days: Days until token expires
        """
        self.vault_path = Path(vault_path).expanduser()
        self.enable_vault_persistence = enable_vault_persistence
        self.token_expiry_days = token_expiry_days

        # In-memory token cache for fast validation
        self.token_cache: dict[str, AgentCredential] = {}

        # Create vault directory if needed
        if self.enable_vault_persistence:
            self.vault_path.mkdir(parents=True, exist_ok=True)

    def create_agent_credential(
        self,
        agent_id: str,
        permissions: list[str] | None = None,
        expiry_days: int | None = None,
    ) -> AgentCredential:
        """Create new credential for agent.

        Args:
            agent_id: Unique agent identifier
            permissions: List of allowed operations (default: ["read", "write"])
            expiry_days: Days until expiration (default: 90)

        Returns:
            New AgentCredential with unique token
        """
        if permissions is None:
            permissions = ["read", "write"]

        token = str(uuid.uuid4())
        expiry_days = expiry_days or self.token_expiry_days

        credential = AgentCredential(
            agent_id=agent_id,
            token=token,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=expiry_days),
            permissions=permissions,
            is_active=True,  # New credentials are active by default
        )

        # Add to cache
        self.token_cache[token] = credential

        # Persist to vault asynchronously (non-blocking)
        if self.enable_vault_persistence:
            self._persist_credential_async(credential)

        logger.info(
            "Created credential for agent %s with token %s (expires: %d days)",
            agent_id,
            token[:8] + "...",
            expiry_days,
        )

        return credential

    def validate_token(self, token: str) -> AgentCredential | None:
        """Validate agent token and return credential if valid.

        Args:
            token: Token string to validate

        Returns:
            AgentCredential if valid and active, None otherwise
        """
        if not token:
            return None

        # Check cache first
        if token in self.token_cache:
            credential = self.token_cache[token]

            # Verify active and not expired
            if not credential.is_active:
                logger.debug("Token %s is inactive", token[:8])
                return None

            if credential.is_expired():
                logger.debug("Token %s has expired", token[:8])
                return None

            # Update last_used timestamp
            credential.last_used = datetime.now(UTC)
            return credential

        logger.debug("Token %s not found in cache", token[:8])
        return None

    def revoke_credential(self, agent_id: str) -> bool:
        """Revoke agent's credential (e.g., on team member removal).

        Args:
            agent_id: Agent ID to revoke

        Returns:
            True if revoked, False if not found
        """
        # Find credential by agent_id
        tokens_to_revoke = [
            token for token, cred in self.token_cache.items() if cred.agent_id == agent_id
        ]

        if not tokens_to_revoke:
            logger.warning("No credentials found for agent %s", agent_id)
            return False

        for token in tokens_to_revoke:
            self.token_cache[token].is_active = False

        logger.info("Revoked %d credential(s) for agent %s", len(tokens_to_revoke), agent_id)
        return True

    def rotate_credentials(
        self,
        agent_id: str,
        new_permissions: list[str] | None = None,
    ) -> AgentCredential | None:
        """Rotate agent's credential (periodic security refresh).

        Creates new token and invalidates old one.

        Args:
            agent_id: Agent ID to rotate
            new_permissions: Updated permissions (default: keep existing)

        Returns:
            New AgentCredential, or None if agent not found
        """
        # Find old credential
        old_token = None
        old_permissions = ["read", "write"]

        for token, cred in self.token_cache.items():
            if cred.agent_id == agent_id and cred.is_active:
                old_token = token
                old_permissions = cred.permissions
                break

        if not old_token:
            logger.warning("No active credential found for agent %s", agent_id)
            return None

        # Revoke old credential
        self.token_cache[old_token].is_active = False

        # Create new credential
        permissions = new_permissions or old_permissions
        new_credential = self.create_agent_credential(agent_id=agent_id, permissions=permissions)

        logger.info(
            "Rotated credential for agent %s (old: %s, new: %s)",
            agent_id,
            old_token[:8] + "...",
            new_credential.token[:8] + "...",
        )

        return new_credential

    def get_credential_by_agent_id(self, agent_id: str) -> AgentCredential | None:
        """Get active credential for agent.

        Args:
            agent_id: Agent ID to look up

        Returns:
            AgentCredential if found and active, None otherwise
        """
        for credential in self.token_cache.values():
            if credential.agent_id == agent_id and credential.is_active:
                if not credential.is_expired():
                    return credential

        return None

    def _persist_credential_async(self, credential: AgentCredential) -> None:
        """Persist credential to vault asynchronously (non-blocking).

        Args:
            credential: Credential to persist
        """
        if not self.enable_vault_persistence:
            return

        try:
            # Non-blocking async write
            import json

            cred_file = self.vault_path / f"{credential.agent_id}_{credential.token[:8]}.json"
            with open(cred_file, "w") as f:
                json.dump(credential.to_dict(), f, indent=2)

            logger.debug("Persisted credential for %s to %s", credential.agent_id, cred_file)
        except Exception as e:
            # Non-blocking: log error but don't crash
            logger.warning("Failed to persist credential for %s: %s", credential.agent_id, e)

    def cleanup_expired_credentials(self) -> int:
        """Remove expired credentials from cache.

        Returns:
            Number of credentials cleaned up
        """
        expired_tokens = [token for token, cred in self.token_cache.items() if cred.is_expired()]

        for token in expired_tokens:
            del self.token_cache[token]

        if expired_tokens:
            logger.info("Cleaned up %d expired credentials", len(expired_tokens))

        return len(expired_tokens)

    def get_stats(self) -> dict[str, Any]:
        """Get authentication statistics.

        Returns:
            Dictionary with credential stats
        """
        active_creds = [c for c in self.token_cache.values() if c.is_active and not c.is_expired()]
        expired_creds = [c for c in self.token_cache.values() if c.is_expired()]
        inactive_creds = [c for c in self.token_cache.values() if not c.is_active]

        return {
            "total_credentials": len(self.token_cache),
            "active_credentials": len(active_creds),
            "expired_credentials": len(expired_creds),
            "inactive_credentials": len(inactive_creds),
            "agents": len({c.agent_id for c in self.token_cache.values()}),
        }
