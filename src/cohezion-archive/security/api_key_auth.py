"""
API Key Authentication Middleware for MCP Server

Provides request-level authentication and authorization for the Cloud Vault MCP server.
All requests must include a valid X-API-Key header.

Security:
- API key stored in environment variable (never hardcoded)
- Invalid key attempts logged for auditing (key redacted)
- Returns 401 Unauthorized on missing/invalid key
- Integrates with Flask app middleware stack
"""

import logging
import os


logger = logging.getLogger(__name__)


class APIKeyValidator:
    """Validates API keys for incoming requests."""

    def __init__(self, env_key: str = "MCP_API_KEY"):
        """
        Initialize validator with API key from environment.

        Args:
            env_key: Environment variable containing the API key
        """
        self.api_key = os.getenv(env_key)
        if not self.api_key:
            logger.warning(
                "No API key configured in environment. Set %s to enable authentication.", env_key
            )

    def validate(self, request_key: str | None) -> bool:
        """
        Validate a request API key.

        Args:
            request_key: The key from the request header

        Returns:
            True if key is valid, False otherwise
        """
        if not self.api_key:
            logger.warning("No API key configured - authentication disabled")
            return True

        if not request_key:
            logger.warning("Request missing X-API-Key header")
            return False

        # Constant-time comparison to prevent timing attacks
        import hmac

        expected_bytes = self.api_key.encode()
        provided_bytes = request_key.encode()

        if not hmac.compare_digest(expected_bytes, provided_bytes):
            logger.warning("Invalid API key provided in request (key redacted)")
            return False

        return True


# Global validator instance
_validator: APIKeyValidator | None = None


def get_validator(env_key: str = "MCP_API_KEY") -> APIKeyValidator:
    """
    Get or create the API key validator instance.

    Args:
        env_key: Environment variable containing the API key

    Returns:
        APIKeyValidator instance
    """
    global _validator
    if _validator is None:
        _validator = APIKeyValidator(env_key)
    return _validator


def reset_validator() -> None:
    """Reset the global validator instance (for testing)."""
    global _validator
    _validator = None
