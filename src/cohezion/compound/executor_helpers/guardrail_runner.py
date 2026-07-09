"""Async guardrail invocation helper for CompoundExecutor (Wave 2D extract).

Provides a sync-context wrapper around async guardrail coroutines. Failure is
non-blocking — logs at debug level and returns None so the caller can proceed
without guardrails when they cannot be evaluated.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any


logger = logging.getLogger(__name__)


def run_async_guardrail(coro: Any) -> Any:
    """Execute async guardrail check in sync context.

    Non-blocking on failure - logs and returns None.

    Args:
        coro: Async coroutine to execute

    Returns:
        Result of coroutine or None on failure
    """
    try:
        return asyncio.run(coro)
    except (TimeoutError, RuntimeError, asyncio.CancelledError) as e:
        logger.debug("Guardrail check failed (non-blocking): %s", e, exc_info=True)
        return None