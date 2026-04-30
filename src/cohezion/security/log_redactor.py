"""
Logging Redaction Filter

Prevents sensitive information (API keys, passwords, tokens, private keys) from
appearing in logs. Applies pattern-based redaction to all log messages.

Security:
- Redacts common secret patterns: API_KEY, password, token, private_key, wallet_key, etc.
- Works with Python's standard logging module
- Applied at handler level (all logs redacted)
- Preserves log structure - only content is masked
"""

import logging
import re
from re import Pattern
from typing import ClassVar


class RedactionFilter(logging.Filter):
    """
    Logging filter that redacts sensitive information from log records.

    Patterns matched:
    - API_KEY=value or apikey=value
    - password=value or PASSWORD=value
    - token=value or TOKEN=value
    - private_key, wallet_key, secret_key
    - Authorization headers (Bearer, Basic)
    - Environment variable exposures
    - JSON Web Tokens (JWT)
    """

    # Patterns to match and redact
    PATTERNS: ClassVar[dict[str, Pattern[str]]] = {
        "api_key": re.compile(
            r"(api[_-]?key|apikey)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]+['\"]?",
            re.IGNORECASE,
        ),
        "password": re.compile(
            r"(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
            re.IGNORECASE,
        ),
        "token": re.compile(
            r"(token|auth|bearer)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]+['\"]?",
            re.IGNORECASE,
        ),
        "private_key": re.compile(
            r"(private[_-]?key|wallet[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]+['\"]?",
            re.IGNORECASE,
        ),
        "bearer_token": re.compile(
            r"(authorization|x-api-key)\s*[:=]\s*['\"]?(Bearer|Basic)\s+[a-zA-Z0-9_\-\.]+['\"]?",
            re.IGNORECASE,
        ),
        "jwt": re.compile(
            r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        ),
        "env_var": re.compile(
            r"\$\{?(api[_-]?key|password|token|secret|key)[}\]?=[^\s)}\]]+",
            re.IGNORECASE,
        ),
    }

    REDACTED_TEXT = "[REDACTED]"

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter a log record, redacting sensitive information.

        Args:
            record: The log record to filter

        Returns:
            True (always pass the record, after redaction)
        """
        # Redact the message
        if record.msg:
            record.msg = self._redact_string(str(record.msg))

        # Redact the formatted message (only redact string args to preserve types)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: self._redact_string(str(value)) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self._redact_string(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def _redact_string(self, text: str) -> str:
        """
        Redact sensitive patterns from a string.

        Args:
            text: The text to redact

        Returns:
            The text with sensitive patterns replaced with [REDACTED]
        """
        for pattern in self.PATTERNS.values():
            text = pattern.sub(self.REDACTED_TEXT, text)

        return text


def setup_redaction(logger_instance: logging.Logger) -> None:
    """
    Add redaction filter to a logger.

    Args:
        logger_instance: The logger to add redaction to
    """
    redaction_filter = RedactionFilter()
    for handler in logger_instance.handlers:
        handler.addFilter(redaction_filter)


def setup_root_redaction() -> None:
    """Add redaction filter to the root logger."""
    redaction_filter = RedactionFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(redaction_filter)


# Apply redaction to root logger on module import
setup_root_redaction()
