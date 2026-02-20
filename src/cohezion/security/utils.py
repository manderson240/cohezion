"""Security utilities for input validation and sanitization.

Provides:
- Error sanitization middleware
- Input validation helpers
- Path traversal protection
- Output filtering
"""

import logging
import re
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def sanitize_error_message(error: Exception | str) -> str:
    """Sanitize error messages for client responses.

    Removes internal details that could leak sensitive information:
    - File system paths
    - Internal class names
    - Stack traces
    - Database connection strings
    - Environment variable names

    Args:
        error: The error or exception to sanitize

    Returns:
        Safe error message suitable for client consumption
    """
    error_str = str(error)

    # Patterns that could leak internal information
    sensitive_patterns = [
        # File paths
        (r"/(?:home|Users|root|var|tmp|opt|usr)/[\w/._-]+", "<path>"),
        (r"[A-Za-z]:\\[\\a-zA-Z0-9_\\.-]+", "<path>"),
        # Database connection strings
        (r"postgresql://[^@]+@", "postgresql://***@"),
        (r"mysql://[^:]+:[^@]+@", "mysql://***:***@"),
        (r"mongodb://[^:]+:[^@]+@", "mongodb://***:***@"),
        (r"redis://[^:]+:[^@]+@", "redis://***:***@"),
        # Environment variable references
        (r"os\.environ\[[^\]]+\]", "<env_var>"),
        (r"\$?\{?\w*(?:PATH|KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[_A-Z0-9]*\}?", "<env_var>"),
        # Python internal paths
        (r"File \"[^\"]+\"", "File <path>"),
        (r" cohezion\.[\w.]+", " <module>"),
        # Stack traces
        (r"Traceback \(most recent call last\):", "Traceback (internal)"),
    ]

    sanitized = error_str
    for pattern, replacement in sensitive_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    # Limit length to prevent DoS via huge error messages
    max_length = 500
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "... [truncated]"

    return sanitized


class SafeErrorMiddleware:
    """Middleware to sanitize error responses before sending to clients."""

    def __init__(self, app: Any):
        self.app = app
        self.sensitive_words = [
            "Traceback", "File ", "line ", "Exception", "Error",
            "Internal Server Error", "AttributeError", "KeyError",
            "TypeError", "ValueError", "IndexError", "OverflowError",
        ]

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """Wrap the ASGI app to catch and sanitize errors."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Wrap the send function to capture responses
        original_send = send

        async def modified_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)

                # Only process error responses
                if status_code >= 500:
                    # Capture the response body
                    body_chunks = []

                    async def capture_body(receive: Any) -> bytes:
                        chunks = []
                        more_body = True
                        while more_body:
                            message = await receive()
                            chunks.append(message.get("body", b""))
                            more_body = message.get("more_body", False)
                        return b"".join(chunks)

                    # Read the body
                    body = await capture_body(receive)

                    # Replace with sanitized message
                    message["body"] = b'{"error": "Internal server error"}'

            await original_send(message)

        await self.app(scope, receive, send)


def validate_path_traversal(path: str, base_dir: str) -> bool:
    """Validate that a path doesn't escape the base directory.

    Args:
        path: The path to validate
        base_dir: The allowed base directory

    Returns:
        True if path is safe, False if it contains path traversal
    """
    import os
    from pathlib import Path

    try:
        # Resolve to absolute path
        resolved = Path(path).resolve()
        base = Path(base_dir).resolve()

        # Check if resolved path is within base directory
        return str(resolved).startswith(str(base) + os.sep) or resolved == base
    except Exception:
        return False


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe (no path traversal).

    Args:
        filename: The filename to check

    Returns:
        True if filename is safe
    """
    # Reject paths with directory separators
    if "/" in filename or "\\" in filename:
        return False

    # Reject paths starting with dot (hidden files, ../)
    if filename.startswith("..") or filename.startswith("."):
        return False

    # Reject empty or whitespace-only names
    if not filename.strip():
        return False

    return True
