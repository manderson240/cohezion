# class attrs treated as immutable config; never mutated per-instance
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

from cohezion._redaction import RedactionFilter as RedactionFilter  # re-export


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
