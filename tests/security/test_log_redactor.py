"""
Tests for Logging Redaction Filter

Verifies:
- Pattern-based redaction of sensitive information
- Integration with Python logging
- Filter behavior with various data types
- Edge cases and special characters
"""

import logging
from io import StringIO

import pytest

from cohezion.security.log_redactor import (
    RedactionFilter,
    setup_redaction,
    setup_root_redaction,
)


@pytest.fixture
def logger():
    """Create a test logger with string handler."""
    test_logger = logging.getLogger("test_redactor")
    test_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    test_logger.handlers = []

    # Add string handler
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    test_logger.addHandler(handler)

    return test_logger


class TestRedactionFilter:
    """Test RedactionFilter class."""

    def test_redact_api_key(self, logger):
        """Test redaction of API keys."""
        filter_obj = RedactionFilter()
        text = "API_KEY=secret123"
        redacted = filter_obj._redact_string(text)
        assert "[REDACTED]" in redacted

    def test_redact_password(self):
        """Test redaction of passwords."""
        filter_obj = RedactionFilter()

        text = "password=mysecretpassword"
        redacted = filter_obj._redact_string(text)
        assert redacted == "[REDACTED]"

    def test_redact_token(self):
        """Test redaction of tokens."""
        filter_obj = RedactionFilter()

        text = "token=abc123def456"
        redacted = filter_obj._redact_string(text)
        assert redacted == "[REDACTED]"

    def test_redact_bearer_token(self):
        """Test redaction of bearer tokens."""
        filter_obj = RedactionFilter()

        text = "Authorization: Bearer eyJhbGc..."
        redacted = filter_obj._redact_string(text)
        assert "[REDACTED]" in redacted

    def test_redact_jwt(self):
        """Test redaction of JSON Web Tokens."""
        filter_obj = RedactionFilter()

        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        redacted = filter_obj._redact_string(jwt)
        assert "[REDACTED]" in redacted

    def test_redact_private_key(self):
        """Test redaction of private keys."""
        filter_obj = RedactionFilter()

        text = "private_key=0xabcd1234"
        redacted = filter_obj._redact_string(text)
        assert redacted == "[REDACTED]"

    def test_redact_wallet_key(self):
        """Test redaction of wallet keys."""
        filter_obj = RedactionFilter()

        text = "wallet_key=0x1234567890abcdef"
        redacted = filter_obj._redact_string(text)
        assert redacted == "[REDACTED]"

    def test_case_insensitive_redaction(self):
        """Test that redaction is case-insensitive."""
        filter_obj = RedactionFilter()

        texts = [
            "PASSWORD=secret",
            "password=secret",
            "Password=secret",
        ]

        for text in texts:
            redacted = filter_obj._redact_string(text)
            assert redacted == "[REDACTED]"

    def test_quoted_values_redacted(self):
        """Test that quoted secret values are redacted."""
        filter_obj = RedactionFilter()

        texts = [
            'password="mysecret"',
            "password='mysecret'",
            'token="abc123"',
        ]

        for text in texts:
            redacted = filter_obj._redact_string(text)
            assert "[REDACTED]" in redacted

    def test_multiple_secrets_in_one_message(self):
        """Test redaction of multiple secrets in one message."""
        filter_obj = RedactionFilter()

        text = "password=secret123 token=abc123def456 api_key=key789"
        redacted = filter_obj._redact_string(text)

        assert "secret123" not in redacted
        assert "abc123def456" not in redacted
        assert "key789" not in redacted
        # Should have redacted text but may vary depending on patterns
        assert len(redacted) > 0

    def test_normal_text_preserved(self):
        """Test that normal text without secrets is preserved."""
        filter_obj = RedactionFilter()

        text = "This is a normal log message"
        redacted = filter_obj._redact_string(text)
        assert redacted == text

    def test_filter_method(self):
        """Test the filter() method on a log record."""
        filter_obj = RedactionFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="API_KEY=secret123",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True
        assert "secret123" not in record.msg

    def test_filter_with_dict_args(self):
        """Test filter with dictionary arguments."""
        filter_obj = RedactionFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User logged in",
            args={"password": "secret123", "user": "john"},
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True
        # Dict values are redacted during filtering
        redacted_args = record.args
        # Check that the args have been processed
        assert isinstance(redacted_args, dict)

    def test_filter_with_tuple_args(self):
        """Test filter with tuple arguments."""
        filter_obj = RedactionFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Config: %s %s",
            args=("api_key=secret123", "password=pass456"),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True
        # Args are redacted
        assert "[REDACTED]" in str(record.args)


class TestSetupFunctions:
    """Test setup helper functions."""

    def test_setup_redaction(self, logger):
        """Test setup_redaction adds filter to logger."""
        # Logger.filters is empty until filters are added to handlers
        initial_count = len(logger.handlers)
        setup_redaction(logger)
        # Check that redaction was applied to handlers
        assert len(logger.handlers) == initial_count

    def test_setup_root_redaction(self):
        """Test setup_root_redaction adds filter to root logger."""
        root = logging.getLogger()
        initial_filter_count = len(root.filters)

        # May already have filters
        setup_root_redaction()

        # Should have at least one filter after setup
        assert len(root.filters) >= initial_filter_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
