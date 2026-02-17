"""Logging Redaction Filter.

Prevents sensitive information (API keys, passwords, tokens, private keys)
from appearing in logs. Applies pattern-based redaction to all log messages.
"""

import logging
import re
from re import Pattern
from typing import ClassVar


class RedactionFilter(logging.Filter):
    """Logging filter that redacts sensitive information from log records."""

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
            r"(private[_-]?key|wallet[_-]?key|secret[_-]?key)"
            r"\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]+['\"]?",
            re.IGNORECASE,
        ),
        "bearer_token": re.compile(
            r"(authorization|x-api-key)"
            r"\s*[:=]\s*['\"]?(Bearer|Basic)\s+[a-zA-Z0-9_\-\.]+['\"]?",
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

    REDACTED_TEXT: ClassVar[str] = "[REDACTED]"

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter a log record, redacting sensitive information."""
        if record.msg:
            record.msg = self._redact_string(str(record.msg))

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: (
                        self._redact_string(value) if isinstance(value, str) else value
                    )
                    for key, value in record.args.items()
                }
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self._redact_string(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def _redact_string(self, text: str) -> str:
        """Redact sensitive patterns from a string."""
        for pattern in self.PATTERNS.values():
            text = pattern.sub(self.REDACTED_TEXT, text)
        return text


def setup_redaction(logger_instance: logging.Logger) -> None:
    """Add redaction filter to a logger."""
    redaction_filter = RedactionFilter()
    for handler in logger_instance.handlers:
        handler.addFilter(redaction_filter)


def setup_root_redaction() -> None:
    """Add redaction filter to the root logger."""
    redaction_filter = RedactionFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(redaction_filter)


setup_root_redaction()
