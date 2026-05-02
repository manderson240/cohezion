"""TEE Key Management — Software-emulated Trusted Execution Environment (Story 1-0-5).

Keys used for intent-action signing are stored in a hardware-isolated namespace
(software-emulated). Direct memory reads from outside the TEE boundary are logged
as security events.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

_TEE_NAMESPACE: dict[str, bytes] = {}  # Software-emulated isolated storage
_SECURITY_EVENTS: list[dict] = []


class KeyAccessMode(Enum):
    GENERATE = "generate"
    SIGN = "sign"
    VERIFY = "verify"


@dataclass
class SecurityEvent:
    """Logged when unauthorized key access is attempted."""

    event_type: str
    key_id: str | None
    details: str
    blocked: bool = True

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "key_id": self.key_id,
            "details": self.details,
            "blocked": self.blocked,
        }


@dataclass
class TEEKeyManager:
    """Software-emulated TEE for signing key isolation.

    Keys are generated within the TEE namespace and never returned as
    plaintext. All signing/verification operations happen inside the boundary.
    """

    _key_ids: list[str] = field(default_factory=list)

    def generate_key(self, key_id: str) -> str:
        """Generate a new signing key stored inside the TEE namespace."""
        raw = secrets.token_bytes(32)
        _TEE_NAMESPACE[key_id] = raw
        self._key_ids.append(key_id)
        logger.debug("TEE: key generated for %s", key_id)
        return key_id  # Return ID only, never the key material

    def sign(self, key_id: str, payload: bytes) -> str:
        """Sign payload using the named key (key never leaves TEE)."""
        raw = self._require_key(key_id, KeyAccessMode.SIGN)
        return hmac.new(raw, payload, hashlib.sha256).hexdigest()

    def verify(self, key_id: str, payload: bytes, signature: str) -> bool:
        """Verify signature using the named key."""
        raw = self._require_key(key_id, KeyAccessMode.VERIFY)
        expected = hmac.new(raw, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def attempt_memory_read(self, key_id: str) -> None:
        """Simulate an attacker attempting direct memory read outside TEE."""
        event = SecurityEvent(
            event_type="UNAUTHORIZED_MEMORY_READ",
            key_id=key_id,
            details=f"Direct memory read attempted for key {key_id} — blocked at TEE boundary",
            blocked=True,
        )
        _SECURITY_EVENTS.append(event.to_dict())
        logger.warning("TEE security event: %s", event.details)
        raise PermissionError(f"TEE boundary violation: key {key_id!r} is not accessible from userspace")

    def has_key(self, key_id: str) -> bool:
        return key_id in _TEE_NAMESPACE

    def security_events(self) -> list[dict]:
        return list(_SECURITY_EVENTS)

    def clear_events(self) -> None:
        _SECURITY_EVENTS.clear()

    def _require_key(self, key_id: str, mode: KeyAccessMode) -> bytes:
        if key_id not in _TEE_NAMESPACE:
            raise KeyError(f"TEE: key {key_id!r} not found")
        return _TEE_NAMESPACE[key_id]
