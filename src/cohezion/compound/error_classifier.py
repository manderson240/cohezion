"""Error classification for compound executor retry/recovery decisions.

Provides a single classify() function that takes an exception and returns
error_category + retryable flag. Extracted to a separate module so the
logic is testable independently and can be imported by executor.py.
"""

from __future__ import annotations

import asyncio
from typing import Any


def classify_error(exc: Exception) -> dict[str, Any]:
    """Classify an exception for retry/recovery decisions.

    Returns:
        dict with keys:
        - error_type: class name of the exception
        - error_category: one of "transient", "resource", "logic", "permanent"
        - retryable: bool — True for transient and resource errors
    """
    e_type = type(exc)

    if e_type in (TimeoutError, asyncio.TimeoutError):
        return {"error_type": e_type.__name__, "error_category": "transient", "retryable": True}
    elif e_type in (MemoryError, OSError, IOError):
        return {"error_type": e_type.__name__, "error_category": "resource", "retryable": True}
    elif e_type in (ValueError, TypeError, AttributeError, KeyError, IndexError):
        return {"error_type": e_type.__name__, "error_category": "logic", "retryable": False}
    else:
        return {"error_type": e_type.__name__, "error_category": "permanent", "retryable": False}
