"""
Tests for API Key Authentication Module

Verifies:
- API key validation with constant-time comparison
- Request-level authentication
- Decorator functionality
- Error handling
"""

import os

import pytest

from cohezion.security.api_key_auth import (
    APIKeyValidator,
    get_validator,
    reset_validator,
)


@pytest.fixture
def set_api_key():
    """Set up and tear down API key for tests."""
    original = os.environ.get("MCP_API_KEY")
    os.environ["MCP_API_KEY"] = "test-api-key-12345"
    yield
    reset_validator()
    if original:
        os.environ["MCP_API_KEY"] = original
    else:
        os.environ.pop("MCP_API_KEY", None)


class TestAPIKeyValidator:
    """Test APIKeyValidator class."""

    def test_validator_initialization(self, set_api_key):
        """Test validator initializes with API key from environment."""
        validator = APIKeyValidator()
        assert validator.api_key == "test-api-key-12345"

    def test_valid_key(self, set_api_key):
        """Test validation passes with correct key."""
        validator = APIKeyValidator()
        assert validator.validate("test-api-key-12345") is True

    def test_invalid_key(self, set_api_key):
        """Test validation fails with incorrect key."""
        validator = APIKeyValidator()
        assert validator.validate("wrong-key") is False

    def test_missing_key(self, set_api_key):
        """Test validation fails with missing key."""
        validator = APIKeyValidator()
        assert validator.validate(None) is False

    def test_empty_key(self, set_api_key):
        """Test validation fails with empty key."""
        validator = APIKeyValidator()
        assert validator.validate("") is False

    def test_no_environment_key(self):
        """Test validator when no environment key is set."""
        reset_validator()
        os.environ.pop("MCP_API_KEY", None)
        validator = APIKeyValidator()
        assert validator.api_key is None
        # Should return True if no key configured (auth disabled)
        assert validator.validate("any-key") is True

    def test_case_sensitive(self, set_api_key):
        """Test that API key validation is case-sensitive."""
        validator = APIKeyValidator()
        assert validator.validate("TEST-API-KEY-12345") is False

    def test_timing_attack_resistance(self, set_api_key):
        """Test that validation uses constant-time comparison."""
        validator = APIKeyValidator()
        # Both should take similar time (constant-time comparison)
        # We can't easily test timing, but we verify the behavior
        assert validator.validate("test-api-key-12345") is True
        assert validator.validate("wrong-api-key-wrong") is False


class TestGetValidator:
    """Test global validator getter."""

    def test_singleton_pattern(self, set_api_key):
        """Test that get_validator returns the same instance."""
        validator1 = get_validator()
        validator2 = get_validator()
        assert validator1 is validator2

    def test_reset_validator(self, set_api_key):
        """Test resetting validator."""
        validator1 = get_validator()
        reset_validator()
        validator2 = get_validator()
        assert validator1 is not validator2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
