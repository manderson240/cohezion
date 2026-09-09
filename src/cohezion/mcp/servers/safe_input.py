"""Shared input sanitization for MCP servers.

Prevents path traversal, command injection, and log injection
across all MCP server endpoints.
"""

from __future__ import annotations

import re
from pathlib import Path


# Safe single path component: blocks traversal, absolute paths, and separators.
_SAFE_COMPONENT_RE = re.compile(r"[A-Za-z0-9._-]{1,128}")


def sanitize_path(user_path: str, base_dir: str | Path) -> Path:
    """Resolve and validate a user-provided path.

    Prevents path traversal attacks by ensuring the resolved path
    stays within the allowed base directory.

    Raises ValueError if path escapes the base directory.
    """
    resolved = Path(user_path).resolve()
    base = Path(base_dir).resolve()

    try:
        resolved.relative_to(base)
    except ValueError:
        msg = f"Path escapes allowed directory: {user_path}"
        raise ValueError(msg) from None

    return resolved


def sanitize_component(component: str) -> str:
    """Validate a user-provided single path component (filename/subdir).

    Returns the component unchanged if it is a safe single path component
    (letters, digits, dot, underscore, dash; 1-128 chars), raises ValueError
    otherwise. Explicitly rejects "." and "..". Prevents traversal like "../"
    or absolute paths at the call site before they are ever joined onto a
    base directory.
    """
    if component in {".", ".."} or not _SAFE_COMPONENT_RE.fullmatch(component):
        msg = f"Unsafe path component: {component!r}"
        raise ValueError(msg)
    return component


def safe_component_or_none(component: str) -> str | None:
    """Like sanitize_component but returns None instead of raising."""
    if component in {".", ".."} or not _SAFE_COMPONENT_RE.fullmatch(component):
        return None
    return component


def sanitize_log(value: str) -> str:
    """Remove newlines and control characters from user input before logging.

    Prevents log injection attacks where attackers embed fake log
    entries via newline characters in user-controlled data.
    """
    return re.sub(r"[\r\n\x00-\x1f\x7f]", " ", str(value))
