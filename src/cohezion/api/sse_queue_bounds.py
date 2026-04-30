"""
SSE Queue Bounds Manager

Prevents unbounded queue growth in SSE endpoints by enforcing maxsize limits
and rejecting new messages when queue is full.

CVSS 6.5 Mitigation: Prevents DoS via memory exhaustion.
"""

import asyncio
import logging
from typing import Any, TypeVar


logger = logging.getLogger(__name__)

T = TypeVar("T")


class BoundedAsyncQueue:
    """Wrapper around asyncio.Queue with maxsize enforcement and overflow handling."""

    def __init__(self, maxsize: int = 1000):
        """
        Initialize bounded queue.

        Args:
            maxsize: Maximum queue size (default 1000)
        """
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self._overflow_count = 0

    def put_nowait_safe(self, item: T) -> bool:
        """
        Put item without blocking, return success status.

        Returns:
            True if item was queued, False if queue is full
        """
        try:
            self._queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            self._overflow_count += 1
            if self._overflow_count % 100 == 0:  # Log every 100 overflows
                logger.warning(
                    f"SSE queue overflow (maxsize={self.maxsize}, total "
                    f"overflows={self._overflow_count})"
                )
            return False

    async def put_async_safe(self, item: T) -> bool:
        """
        Put item asynchronously, return success status.

        Returns:
            True if item was queued, False if queue timeout expires
        """
        try:
            # Try to put with timeout to prevent indefinite blocking
            await asyncio.wait_for(self._queue.put(item), timeout=1.0)
            return True
        except TimeoutError:
            self._overflow_count += 1
            logger.warning(
                f"SSE queue put timeout (maxsize={self.maxsize}, total "
                f"overflows={self._overflow_count})"
            )
            return False

    async def get(self) -> T:
        """Get item from queue (async)."""
        return await self._queue.get()

    def put_nowait(self, item: T) -> None:
        """Put item without blocking (raises QueueFull if full)."""
        self._queue.put_nowait(item)

    def qsize(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "current_size": self.qsize(),
            "maxsize": self.maxsize,
            "overflow_count": self._overflow_count,
            "usage_percent": (self.qsize() / self.maxsize * 100) if self.maxsize else 0,
        }


def create_bounded_queue(maxsize: int = 1000) -> BoundedAsyncQueue:
    """
    Create a bounded async queue.

    Args:
        maxsize: Maximum queue size

    Returns:
        BoundedAsyncQueue instance
    """
    return BoundedAsyncQueue(maxsize=maxsize)


async def safe_queue_put(queue: asyncio.Queue, item: Any, max_retries: int = 3) -> bool:
    """
    Safely put item in queue with retries.

    Args:
        queue: Target queue
        item: Item to put
        max_retries: Number of retry attempts

    Returns:
        True if item was queued, False if all retries failed
    """
    for attempt in range(max_retries):
        try:
            queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.01 * (2**attempt))  # Exponential backoff
            else:
                logger.warning(f"Failed to queue item after {max_retries} retries (queue full)")
                return False

    return False
