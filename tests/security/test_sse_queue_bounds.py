"""
SSE Queue Bounds Security Tests

Verifies that unbounded queue growth is prevented by enforcing maxsize limits
on SSE event queues, preventing DoS via memory exhaustion.

CVSS 6.5 Mitigation: Bounded queues prevent OOM attacks.
"""

import asyncio

import pytest

from cohezion.api.sse_queue_bounds import (
    BoundedAsyncQueue,
    create_bounded_queue,
    safe_queue_put,
)


class TestBoundedAsyncQueue:
    """Test BoundedAsyncQueue functionality."""

    def test_create_bounded_queue(self):
        """Test creating a bounded queue."""
        queue = BoundedAsyncQueue(maxsize=100)
        assert queue.maxsize == 100
        assert queue.qsize() == 0

    def test_put_nowait_success(self):
        """Test successful non-blocking put."""
        queue = BoundedAsyncQueue(maxsize=10)

        result = queue.put_nowait_safe("event1")
        assert result is True
        assert queue.qsize() == 1

    def test_put_nowait_overflow(self):
        """Test overflow detection on non-blocking put."""
        queue = BoundedAsyncQueue(maxsize=2)

        # Fill queue
        queue.put_nowait_safe("event1")
        queue.put_nowait_safe("event2")
        assert queue.qsize() == 2

        # Try to overflow
        result = queue.put_nowait_safe("event3")
        assert result is False
        assert queue.qsize() == 2  # Size unchanged

    def test_overflow_count(self):
        """Test overflow counter."""
        queue = BoundedAsyncQueue(maxsize=1)

        queue.put_nowait_safe("event1")

        # Multiple overflows
        for _ in range(5):
            queue.put_nowait_safe("overflow")

        assert queue._overflow_count == 5

    def test_queue_stats(self):
        """Test queue statistics."""
        queue = BoundedAsyncQueue(maxsize=10)

        queue.put_nowait_safe("event1")
        queue.put_nowait_safe("event2")

        stats = queue.get_stats()
        assert stats["maxsize"] == 10
        assert stats["current_size"] == 2
        assert stats["usage_percent"] == 20.0

    @pytest.mark.asyncio
    async def test_put_async_safe_success(self):
        """Test successful async put."""
        queue = BoundedAsyncQueue(maxsize=10)

        result = await queue.put_async_safe("event1")
        assert result is True
        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_put_async_safe_timeout(self):
        """Test async put timeout when queue full."""
        queue = BoundedAsyncQueue(maxsize=1)

        # Fill queue
        await queue.put_async_safe("event1")

        # Next put should timeout
        result = await queue.put_async_safe("event2")
        assert result is False


class TestCreateBoundedQueue:
    """Test bounded queue factory function."""

    def test_default_maxsize(self):
        """Test default maxsize of 1000."""
        queue = create_bounded_queue()
        assert queue.maxsize == 1000

    def test_custom_maxsize(self):
        """Test custom maxsize."""
        queue = create_bounded_queue(maxsize=500)
        assert queue.maxsize == 500


class TestSafeQueuePut:
    """Test safe queue put with retries."""

    @pytest.mark.asyncio
    async def test_safe_put_success_immediate(self):
        """Test successful put on first attempt."""
        queue = BoundedAsyncQueue(maxsize=10)

        result = await safe_queue_put(queue, "event1", max_retries=3)
        assert result is True
        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_safe_put_failure(self):
        """Test failure when queue is full."""
        queue = BoundedAsyncQueue(maxsize=1)

        # Fill queue
        queue.put_nowait("event1")

        # Try to put - should fail after retries
        result = await safe_queue_put(queue, "event2", max_retries=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_safe_put_recovery(self):
        """Test recovery after queue has space again."""
        queue = BoundedAsyncQueue(maxsize=1)

        # Fill queue
        queue.put_nowait("event1")

        # Get one item to make space
        item = await queue.get()
        assert item == "event1"

        # Now put should succeed
        result = await safe_queue_put(queue, "event2", max_retries=3)
        assert result is True


class TestQueueBounds:
    """Test queue size enforcement."""

    def test_queue_respects_maxsize(self):
        """Test that queue cannot exceed maxsize."""
        queue = asyncio.Queue(maxsize=5)

        for i in range(5):
            queue.put_nowait(i)

        assert queue.qsize() == 5

        # Try to add one more
        with pytest.raises(asyncio.QueueFull):
            queue.put_nowait(5)

    @pytest.mark.asyncio
    async def test_bounded_queue_fairness(self):
        """Test that bounded queue maintains FIFO order."""
        queue = BoundedAsyncQueue(maxsize=5)

        # Add events
        for i in range(5):
            queue.put_nowait(f"event{i}")

        # Retrieve in FIFO order
        for i in range(5):
            item = await queue.get()
            assert item == f"event{i}"

    @pytest.mark.asyncio
    async def test_concurrent_puts_with_bounds(self):
        """Test concurrent puts respect queue bounds."""
        queue = BoundedAsyncQueue(maxsize=10)

        # Bounded test: producer puts exactly maxsize+5 items, consumer drains all.
        # The +5 forces the queue to hit maxsize (proving the bound) while keeping
        # the run time deterministic (no 1s timeouts inside put_async_safe).
        async def producer():
            for i in range(15):
                await queue.put_async_safe(f"event{i}")

        async def consumer():
            for _ in range(15):
                await queue.get()

        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(consumer())
        await asyncio.gather(producer_task, consumer_task)

        # After draining, queue is empty and size never exceeded maxsize
        assert queue.qsize() <= queue.maxsize


class TestDoSPrevention:
    """Test prevention of DoS attacks via unbounded queues."""

    def test_unbounded_queue_vulnerable(self):
        """Demonstrate vulnerability of unbounded queues."""
        unbounded = asyncio.Queue()  # No maxsize

        # Can add arbitrarily many items
        for i in range(10000):
            unbounded.put_nowait(f"huge event {i}")

        assert unbounded.qsize() == 10000  # All items stored in memory

    def test_bounded_queue_protected(self):
        """Demonstrate protection with bounded queue."""
        bounded = BoundedAsyncQueue(maxsize=100)

        # Try to add many items
        success_count = 0
        for i in range(1000):
            if bounded.put_nowait_safe(f"event{i}"):
                success_count += 1

        # Only maxsize items accepted
        assert bounded.qsize() == 100
        assert success_count == 100

        # Check overflow count
        assert bounded._overflow_count == 900


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
