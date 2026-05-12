"""MCP Authentication - Ephemeral token management for local security."""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path


logger = logging.getLogger(__name__)


# Default path for the auth token
AUTH_TOKEN_PATH = Path.home() / ".cohezion" / "auth.token"


def generate_ephemeral_token() -> str:
    """Generate a new random ephemeral token and save it securely.

    The token is saved with 600 permissions to ensure only the user can read it.
    """
    token = secrets.token_urlsafe(32)

    # Ensure directory exists
    AUTH_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write token with strict permissions
    # We use os.open with O_CREAT | O_WRONLY | O_TRUNC to ensure we can set mode
    fd = os.open(str(AUTH_TOKEN_PATH), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token)

    return token


def get_current_token() -> str | None:
    """Read the current ephemeral token from disk."""
    if not AUTH_TOKEN_PATH.exists():
        return None

    try:
        return AUTH_TOKEN_PATH.read_text().strip()
    except (OSError, ValueError) as e:
        # Fail-closed but NOT silent — operator needs to know why all A2A
        # requests are 403'ing. (Ω12 P1 Patch 12)
        logger.warning(
            "Failed to read ephemeral token from %s: %s", AUTH_TOKEN_PATH, e
        )
        return None


def validate_token(token: str) -> bool:
    """Validate a provided token against the current ephemeral token."""
    current = get_current_token()
    if not current:
        return False
    return secrets.compare_digest(current, token)


def clear_token() -> None:
    """Delete the ephemeral token file."""
    if AUTH_TOKEN_PATH.exists():
        AUTH_TOKEN_PATH.unlink()
