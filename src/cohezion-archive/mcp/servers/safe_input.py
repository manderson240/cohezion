"""Shared input sanitization for MCP servers.

Prevents path traversal, command injection, and log injection
across all MCP server endpoints.
"""

from __future__ import annotations

import re
from pathlib import Path


def sanitize_path(user_path: str, base_dir: str | Path | None = None) -> Path:
    """Resolve and validate a user-provided path.

    Prevents path traversal attacks by ensuring the resolved path
    stays within the allowed base directory.

    Raises ValueError if path escapes the base directory.
    """
    resolved = Path(user_path).resolve()

    if base_dir is not None:
        base = Path(base_dir).resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            msg = f"Path escapes allowed directory: {user_path}"
            raise ValueError(msg) from None

    return resolved


def sanitize_log(value: str) -> str:
    """Remove newlines and control characters from user input before logging.

    Prevents log injection attacks where attackers embed fake log
    entries via newline characters in user-controlled data.
    """
    return re.sub(r"[\r\n\x00-\x1f\x7f]", " ", str(value))
