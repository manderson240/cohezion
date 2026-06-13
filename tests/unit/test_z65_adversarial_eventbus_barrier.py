"""Adversarial batch Z65: event_bus backpressure + delivered-count inflation,
memory_barrier silent re-allocation.

Real bugs found:
1. EventBus.publish() uses put() which blocks on a full queue — QueueFull is
   never raised, the drop path is dead code, publish() hangs indefinitely.
2. EventBus._dispatch() counts crashed handlers as 'delivered' because
   _safe_handle() swallows exceptions and returns None, making every result
   appear successful.
3. MemoryMappedBarrier.allocate() silently returns the original allocation
   when an ID is re-requested with a larger size — caller gets wrong capacity.
"""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Module 1: core/event_bus.py — backpressure and delivered-count bugs
# ---------------------------------------------------------------------------


class TestEventBusBackpressure:
    def _make_bus(self, max_queue_size=2):
        from cohezion.core.event_bus import EventBus

        return EventBus(max_queue_size=max_queue_size)

    def _make_event(self, priority=0):
        from cohezion.core.event_bus import Event, EventType

        return Event(type=EventType.CUSTOM, source="test", priority=priority)

    def test_publish_returns_false_when_queue_full(self):
        """publish() must return False immediately when the queue is full.

        BUG: publish() calls await self._queue.put() which BLOCKS when the queue
        is full rather than raising QueueFull. The 'except asyncio.QueueFull'
        branch is dead code that never executes. Fix: use put_nowait().
        """

        async def run():
            bus = self._make_bus(max_queue_size=2)
            e = self._make_event()

            # Fill queue directly (no processor running to drain it)
            bus._queue.put_nowait((-0, e))
            bus._queue.put_nowait((-0, e))
            assert bus._queue.full()

            # publish() must return False promptly, not block
            result = await asyncio.wait_for(bus.publish(e), timeout=0.2)
            return result

        result = asyncio.run(run())
        assert result is False, "publish() must return False on a full queue, not block"

    def test_dropped_metric_increments_on_full_queue(self):
        """metrics['dropped'] must increment when an event cannot be enqueued."""

        async def run():
            bus = self._make_bus(max_queue_size=1)
            e = self._make_event()

            bus._queue.put_nowait((-0, e))  # fill to capacity
            await asyncio.wait_for(bus.publish(e), timeout=0.2)
            return bus.get_metrics()["dropped"]

        dropped = asyncio.run(run())
        assert dropped == 1, f"Expected dropped=1, got {dropped}"

    def test_published_metric_not_incremented_on_drop(self):
        """metrics['published'] must NOT increment when an event is dropped."""

        async def run():
            bus = self._make_bus(max_queue_size=1)
            e = self._make_event()

            bus._queue.put_nowait((-0, e))
            await asyncio.wait_for(bus.publish(e), timeout=0.2)
            return bus.get_metrics()["published"]

        published = asyncio.run(run())
        assert published == 0, f"Expected published=0 on drop, got {published}"

    def test_successful_publish_increments_published(self):
        """Successful publish() increments published metric and returns True."""

        async def run():
            bus = self._make_bus(max_queue_size=10)
            e = self._make_event()
            result = await bus.publish(e)
            return result, bus.get_metrics()["published"]

        result, published = asyncio.run(run())
        assert result is True
        assert published == 1


class TestEventBusDeliveredCount:
    def test_crashed_handler_not_counted_as_delivered(self):
        """A handler that raises must NOT be counted as a delivered event.

        BUG: _safe_handle() catches exceptions and returns None implicitly.
        _dispatch() checks 'r is None' to count delivered events, so crashed
        handlers count as delivered. Fix: return True on success, False on error.
        """

        async def run():
            from cohezion.core.event_bus import Event, EventBus, EventType

            bus = EventBus()
            e = Event(type=EventType.CUSTOM, source="test")

            async def crashing_handler(event):
                raise RuntimeError("intentional crash")

            bus._handlers[EventType.CUSTOM].append(crashing_handler)
            await bus._dispatch(e)
            return bus._metrics["delivered"], bus._metrics["errors"]

        delivered, errors = asyncio.run(run())
        assert errors == 1
        assert delivered == 0, (
            f"Crashed handler must not count as delivered (got delivered={delivered})"
        )

    def test_successful_handler_counted_as_delivered(self):
        """A handler that completes without error IS counted as delivered."""

        async def run():
            from cohezion.core.event_bus import Event, EventBus, EventType

            bus = EventBus()
            e = Event(type=EventType.CUSTOM, source="test")

            async def good_handler(event):
                pass

            bus._handlers[EventType.CUSTOM].append(good_handler)
            await bus._dispatch(e)
            return bus._metrics["delivered"]

        delivered = asyncio.run(run())
        assert delivered == 1

    def test_mixed_handlers_counts_only_successes(self):
        """With one good and one crashing handler, delivered must be 1, errors 1."""

        async def run():
            from cohezion.core.event_bus import Event, EventBus, EventType

            bus = EventBus()
            e = Event(type=EventType.CUSTOM, source="test")

            async def good(event):
                pass

            async def bad(event):
                raise ValueError("boom")

            bus._handlers[EventType.CUSTOM].extend([good, bad])
            await bus._dispatch(e)
            return bus._metrics["delivered"], bus._metrics["errors"]

        delivered, errors = asyncio.run(run())
        assert delivered == 1
        assert errors == 1


# ---------------------------------------------------------------------------
# Module 2: security/memory_barrier.py — silent re-allocation size mismatch
# ---------------------------------------------------------------------------


class TestMemoryBarrierReAllocation:
    def _make_barrier(self):
        from cohezion.security.memory_barrier import MemoryMappedBarrier

        return MemoryMappedBarrier()

    def test_reallocate_with_larger_size_is_rejected_or_resized(self):
        """Re-allocating an existing ID with a larger size must not silently
        return the original (smaller) allocation.

        BUG: allocate() returns self._allocations[allocation_id] immediately if
        the ID exists, regardless of the requested size. A process that needs
        more GTT space gets the original allocation with no error or warning —
        it will silently read out-of-bounds later.
        Fix: raise ValueError on size mismatch, or reallocate with new size.
        """
        barrier = self._make_barrier()
        a1 = barrier.allocate("proc1", 1024)
        assert a1.size_bytes == 1024

        # Re-request with larger size must not silently return old allocation
        with pytest.raises((ValueError, MemoryError)):
            barrier.allocate("proc1", 4096)

    def test_reallocate_same_size_is_idempotent(self):
        """Re-allocating with the exact same size is safe and returns the same range."""
        barrier = self._make_barrier()
        a1 = barrier.allocate("proc1", 512)
        a2 = barrier.allocate("proc1", 512)  # identical — must be idempotent
        assert a1.base_address == a2.base_address
        assert a1.size_bytes == a2.size_bytes

    def test_boundary_read_at_last_valid_byte(self):
        """Reading at end_address - 1 (last valid byte) must succeed."""
        barrier = self._make_barrier()
        alloc = barrier.allocate("p1", 64)
        last_valid = alloc.end_address - 1
        assert barrier.read("p1", last_valid) is True

    def test_boundary_read_at_end_address_raises(self):
        """Reading at end_address (one past end) must raise BarrierViolationError."""
        from cohezion.security.memory_barrier import BarrierViolationError

        barrier = self._make_barrier()
        alloc = barrier.allocate("p1", 64)
        with pytest.raises(BarrierViolationError):
            barrier.read("p1", alloc.end_address)
