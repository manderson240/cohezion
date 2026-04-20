"""Tests for Memory-Mapped Barrier Isolation (Story 1.6)."""

from __future__ import annotations

import pytest

from cohezion.security.memory_barrier import BarrierViolationError, MemoryMappedBarrier


class TestMemoryMappedBarrier:
    def test_in_bounds_read_succeeds(self):
        barrier = MemoryMappedBarrier()
        alloc = barrier.allocate("proc-1", size_bytes=4096)
        result = barrier.read("proc-1", alloc.base_address)
        assert result is True

    def test_out_of_bounds_read_blocked(self):
        barrier = MemoryMappedBarrier()
        alloc = barrier.allocate("proc-2", size_bytes=4096)
        with pytest.raises(BarrierViolationError, match="GTT bounds violation"):
            barrier.read("proc-2", alloc.end_address)  # Past end

    def test_violation_logged_as_barrier_event(self):
        barrier = MemoryMappedBarrier()
        alloc = barrier.allocate("proc-3", size_bytes=1024)
        with pytest.raises(BarrierViolationError):
            barrier.read("proc-3", alloc.base_address - 1)
        events = barrier.barrier_events()
        assert len(events) == 1
        assert events[0]["allocation_id"] == "proc-3"
        assert events[0]["blocked"] is True

    def test_quota_exceeded_denied(self):
        barrier = MemoryMappedBarrier()
        quota = 1024 * 1024  # 1MB quota
        with pytest.raises(BarrierViolationError, match="Quota exceeded"):
            barrier.deny_over_quota_allocation("malicious-slm", quota * 10, quota)

    def test_quota_exceeded_logged(self):
        barrier = MemoryMappedBarrier()
        with pytest.raises(BarrierViolationError):
            barrier.deny_over_quota_allocation("slm-1", 9999, 100)
        events = barrier.barrier_events()
        assert any(e["event_type"] == "quota_exceeded" for e in events)

    def test_unknown_allocation_raises(self):
        barrier = MemoryMappedBarrier()
        with pytest.raises(KeyError):
            barrier.read("unknown", 0x1000)

    def test_multiple_independent_allocations(self):
        barrier = MemoryMappedBarrier()
        a1 = barrier.allocate("p1", 4096)
        a2 = barrier.allocate("p2", 4096)
        # p1 reads inside p2's range → should be blocked
        with pytest.raises(BarrierViolationError):
            barrier.read("p1", a2.base_address)
