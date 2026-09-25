# class attrs treated as immutable config; never mutated per-instance
"""Secret redaction for log records, installed process-wide by ``import cohezion``.

Lives at the top level (depends only on ``logging`` and ``re``) so that installing it never
imports a package facade. ``cohezion.security.log_redactor`` re-exports ``RedactionFilter``.

Why a record factory rather than a handler filter: a handler filter only covers handlers that
exist when it is attached. Until 2026-09-25 the root handler that received it was created as an
import side effect of ``security/adversarial_tester.py`` (``logging.basicConfig``), reached via
the eager ``cohezion.core`` facade -- redaction was on or off depending on import order. The
factory redacts every record at creation, whatever handlers exist and whenever they were made.
See docs/audits/DYNAMIC_MODULARITY_AUDIT_2026-09-24.md (R1).
"""

from __future__ import annotations

import contextlib
import logging
import re
from re import Pattern
from typing import Any


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
    PATTERNS: dict[str, Pattern[str]] = {
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


def install_record_redaction() -> bool:
    """Redact every LogRecord at creation. Idempotent; returns True if newly installed."""
    previous = logging.getLogRecordFactory()
    if getattr(previous, "_cohezion_redacting", False):
        return False
    redactor = RedactionFilter()

    def _redacting_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        # Redact the FORMATTED message: a secret usually spans template and args
        # ("password=%s", secret), which redacting msg and args separately misses -- and
        # rewriting only the template leaves "%s" consumed and the args unformattable.
        # Records with nothing to redact are left untouched (msg/args preserved).
        try:
            message = record.getMessage()
        except (TypeError, ValueError):  # malformed call: logging reports it later as usual
            with contextlib.suppress(TypeError, ValueError, AttributeError):
                redactor.filter(record)
            return record
        redacted = redactor._redact_string(message)
        if redacted != message:
            record.msg, record.args = redacted, ()
        return record

    _redacting_factory._cohezion_redacting = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(_redacting_factory)
    return True
