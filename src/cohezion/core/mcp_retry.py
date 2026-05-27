"""MCP client retry logic for transient failures.

Provides an exponential backoff retry wrapper for MCPClient operations.
Designed to handle connection failures, timeouts, and transient errors
without blocking the main thread.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar


logger = logging.getLogger(__name__)
T = TypeVar("T")


async def retry_async(
    fn: Callable[..., Any],
    *args,
    max_retries: int = 3,
    base_delay_s: float = 0.5,
    max_delay_s: float = 5.0,
    retryable_types: tuple = (ConnectionError, TimeoutError),
    **kwargs,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        fn: Async callable to retry
        *args: Positional arguments for fn
        max_retries: Maximum number of retry attempts
        base_delay_s: Initial delay between retries (seconds)
        max_delay_s: Maximum delay between retries (seconds)
        retryable_types: Exception types that trigger retries
        **kwargs: Keyword arguments for fn

    Returns:
        Result from successful fn call

    Raises:
        Last exception if all retries exhausted
    """
    last_exc: Exception | None = None
    delay = base_delay_s

    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except retryable_types as e:
            last_exc = e
            if attempt < max_retries:
                logger.debug(
                    "retry_async: attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    type(e).__name__,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, max_delay_s)
            else:
                logger.debug("retry_async: all %d attempts exhausted", max_retries)

    raise last_exc


def retry_sync(
    fn: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay_s: float = 0.1,
    max_delay_s: float = 2.0,
    retryable_types: tuple = (ConnectionError, TimeoutError),
    **kwargs,
) -> T:
    """Retry a synchronous function with exponential backoff."""
    last_exc: Exception | None = None
    delay = base_delay_s

    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except retryable_types as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(delay)
                delay = min(delay * 2, max_delay_s)

    raise last_exc
