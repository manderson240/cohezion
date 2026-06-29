"""
Authentication - API keys and JWT tokens.

Provides:
- API key verification
- JWT token creation and validation
- Role-based access control
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext


logger = logging.getLogger(__name__)

# Configuration
_SECRET_KEY = os.environ.get("COHEZION_SECRET_KEY")
if not _SECRET_KEY:
    raise RuntimeError(
        "COHEZION_SECRET_KEY environment variable is required. "
        "Set it before starting the application."
    )
SECRET_KEY: str = _SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API Keys (loaded from secure storage)
_API_KEY_ENV = os.environ.get("COHEZION_API_KEY")
API_KEYS: dict[str, dict[str, Any]] = (
    {
        _API_KEY_ENV: {
            "name": "default",
            "role": "admin",
            "enabled": True,
        }
    }
    if _API_KEY_ENV
    else {}
)


class AuthError(Exception):
    """Authentication error."""

    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def verify_api_key(api_key: str) -> dict[str, Any]:
    """
    Verify an API key.

    Args:
        api_key: The API key to verify

    Returns:
        API key metadata if valid

    Raises:
        AuthError if invalid
    """
    if not api_key:
        raise AuthError("API key required", "missing_key")

    key_data = API_KEYS.get(api_key)
    if not key_data:
        raise AuthError("Invalid API key", "invalid_key")

    if not key_data.get("enabled", True):
        raise AuthError("API key disabled", "disabled_key")

    return key_data


def create_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT token.

    Args:
        data: Payload data
        expires_delta: Token lifetime

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Token payload if valid

    Raises:
        AuthError if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError as e:
        raise AuthError(f"Invalid token: {e}", "invalid_token") from e


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)  # type: ignore[no-any-return]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]


def check_role(user_role: str, required_role: str) -> bool:
    """
    Check if user has required role.

    Role hierarchy: admin > user > readonly
    """
    roles = {"admin": 3, "user": 2, "readonly": 1}
    return roles.get(user_role, 0) >= roles.get(required_role, 0)
