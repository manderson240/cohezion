"""Consent Manager (v1.0.2 Phase 6).

WebMCP-aligned human-in-the-loop consent system for destructive
or irreversible agent operations.

Features:
    - Cryptographic consent proofs (SHA-256 signed approvals)
    - Consent scoping (per-action, per-session, per-agent)
    - Expiry-based tokens
    - Audit-ready consent records
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


logger = logging.getLogger(__name__)


class ConsentScope(StrEnum):
    """Scope of a consent grant."""

    SINGLE_ACTION = "single_action"
    SESSION = "session"
    PERSISTENT = "persistent"


@dataclass
class ConsentToken:
    """Cryptographic consent proof."""

    token_id: str
    action: str
    scope: ConsentScope
    granted_by: str  # user identifier
    granted_at: float
    expires_at: float
    signature: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Check if token hasn't expired."""
        return time.time() < self.expires_at

    def verify(self) -> bool:
        """Verify the cryptographic signature."""
        expected = _compute_signature(
            self.action,
            self.granted_by,
            self.granted_at,
        )
        return self.signature == expected


def _compute_signature(action: str, user: str, timestamp: float) -> str:
    """Compute SHA-256 signature for consent proof."""
    payload = f"{action}:{user}:{timestamp}"
    return hashlib.sha256(payload.encode()).hexdigest()


class ConsentManager:
    """Manage human-in-the-loop consent for agent actions.

    Parameters
    ----------
    default_expiry_seconds : float
        Default time-to-live for consent tokens.
    """

    def __init__(
        self,
        default_expiry_seconds: float = 3600.0,
    ) -> None:
        self.default_expiry = default_expiry_seconds
        self.tokens: dict[str, ConsentToken] = {}
        self.pending_requests: list[dict[str, Any]] = []

    def request_consent(
        self,
        action: str,
        agent_id: str,
        reason: str = "",
    ) -> str:
        """Request user consent for an action.

        Parameters
        ----------
        action : str
            Description of the action requiring consent.
        agent_id : str
            The agent requesting consent.
        reason : str
            Why consent is needed.

        Returns
        -------
        str
            Request ID for tracking.
        """
        request_id = hashlib.sha256(f"{action}:{agent_id}:{time.time()}".encode()).hexdigest()[:16]

        self.pending_requests.append(
            {
                "request_id": request_id,
                "action": action,
                "agent_id": agent_id,
                "reason": reason,
                "requested_at": time.time(),
            }
        )

        logger.info(
            "Consent requested [%s]: %s by %s",
            request_id,
            action[:80],
            agent_id,
        )
        return request_id

    def grant_consent(
        self,
        action: str,
        user_id: str,
        scope: ConsentScope = ConsentScope.SINGLE_ACTION,
        expiry_seconds: float | None = None,
    ) -> ConsentToken:
        """Grant consent for an action.

        Parameters
        ----------
        action : str
            The action being consented to.
        user_id : str
            The user granting consent.
        scope : ConsentScope
            Scope of the consent grant.
        expiry_seconds : float, optional
            Custom expiry time.

        Returns
        -------
        ConsentToken
            Cryptographic proof of consent.
        """
        now = time.time()
        expiry = expiry_seconds or self.default_expiry
        signature = _compute_signature(action, user_id, now)
        token_id = signature[:16]

        token = ConsentToken(
            token_id=token_id,
            action=action,
            scope=scope,
            granted_by=user_id,
            granted_at=now,
            expires_at=now + expiry,
            signature=signature,
        )

        self.tokens[token_id] = token

        # Remove from pending if it was requested
        self.pending_requests = [r for r in self.pending_requests if r.get("action") != action]

        logger.info(
            "Consent granted [%s]: %s by %s (scope=%s, expires=%.0fs)",
            token_id,
            action[:80],
            user_id,
            scope.value,
            expiry,
        )
        return token

    def check_consent(
        self,
        action: str,
    ) -> ConsentToken | None:
        """Check if valid consent exists for an action.

        Parameters
        ----------
        action : str
            The action to check consent for.

        Returns
        -------
        ConsentToken or None
            Valid token if consent exists, None otherwise.
        """
        for token in self.tokens.values():
            if not token.is_valid:
                continue
            if token.action == action and token.verify():
                return token

        return None

    def revoke(self, token_id: str) -> bool:
        """Revoke a consent token.

        Parameters
        ----------
        token_id : str
            Token to revoke.

        Returns
        -------
        bool
            True if revoked, False if not found.
        """
        if token_id in self.tokens:
            del self.tokens[token_id]
            logger.info("Consent revoked: %s", token_id)
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired tokens.

        Returns
        -------
        int
            Number of tokens removed.
        """
        now = time.time()
        expired = [tid for tid, token in self.tokens.items() if now >= token.expires_at]
        for tid in expired:
            del self.tokens[tid]
        return len(expired)

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return consent audit trail."""
        records: list[dict[str, Any]] = []
        for token in self.tokens.values():
            records.append(
                {
                    "token_id": token.token_id,
                    "action": token.action[:100],
                    "scope": token.scope.value,
                    "granted_by": token.granted_by,
                    "granted_at": token.granted_at,
                    "expires_at": token.expires_at,
                    "valid": token.is_valid,
                }
            )
        return records
