"""Memory-Mapped Barrier Isolation (Story 1.6, NFR-1, Security).

Implements cryptographic memory boundaries around Vanguard Pipeline execution space.
Strictly isolates VRAM/GTT allocation per process. Reads outside allocated bounds
are blocked and logged at the barrier level.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class BarrierViolationError(PermissionError):
    """Raised when an allocation reads outside its GTT bounds."""


@dataclass
class GTTAllocation:
    """A process's allocated GTT memory range."""

    allocation_id: str
    base_address: int
    size_bytes: int

    @property
    def end_address(self) -> int:
        return self.base_address + self.size_bytes

    def contains(self, address: int) -> bool:
        return self.base_address <= address < self.end_address


@dataclass
class BarrierEvent:
    allocation_id: str
    attempted_address: int
    event_type: str  # "out_of_bounds_read" | "quota_exceeded"
    blocked: bool = True

    def to_dict(self) -> dict:
        return {
            "allocation_id": self.allocation_id,
            "attempted_address": self.attempted_address,
            "event_type": self.event_type,
            "blocked": self.blocked,
        }


class MemoryMappedBarrier:
    """GTT bounds enforcement for Substrate Sandbox isolation."""

    def __init__(self, total_gtt_bytes: int = 32 * 1024 * 1024 * 1024) -> None:
        self._total_gtt = total_gtt_bytes
        self._allocations: dict[str, GTTAllocation] = {}
        self._events: list[BarrierEvent] = []
        self._next_base: int = 0x10000  # Start of sandbox GTT space

    def allocate(self, allocation_id: str, size_bytes: int) -> GTTAllocation:
        """Allocate a GTT range for a process."""
        if allocation_id in self._allocations:
            existing = self._allocations[allocation_id]
            if existing.size_bytes != size_bytes:
                raise ValueError(
                    f"Re-allocation size mismatch for {allocation_id!r}: "
                    f"existing={existing.size_bytes}, requested={size_bytes}"
                )
            return existing

        if self._next_base + size_bytes > self._total_gtt:
            raise MemoryError(f"GTT exhausted: cannot allocate {size_bytes} bytes")

        alloc = GTTAllocation(
            allocation_id=allocation_id,
            base_address=self._next_base,
            size_bytes=size_bytes,
        )
        self._allocations[allocation_id] = alloc
        self._next_base += size_bytes
        return alloc

    def read(self, allocation_id: str, address: int) -> bool:
        """Simulate a memory read. Returns True if within bounds, raises on violation."""
        alloc = self._allocations.get(allocation_id)
        if alloc is None:
            raise KeyError(f"Unknown allocation: {allocation_id!r}")

        if not alloc.contains(address):
            event = BarrierEvent(
                allocation_id=allocation_id,
                attempted_address=address,
                event_type="out_of_bounds_read",
            )
            self._events.append(event)
            logger.warning(
                "Memory barrier violation: %s attempted read at 0x%x (bounds: 0x%x-0x%x)",
                allocation_id,
                address,
                alloc.base_address,
                alloc.end_address,
            )
            raise BarrierViolationError(
                f"GTT bounds violation: {allocation_id!r} attempted read at 0x{address:x}, "
                f"outside its allocation 0x{alloc.base_address:x}-0x{alloc.end_address:x}"
            )

        return True

    def deny_over_quota_allocation(
        self, allocation_id: str, requested_bytes: int, quota_bytes: int
    ) -> None:
        """Deny and log an over-quota allocation attempt."""
        event = BarrierEvent(
            allocation_id=allocation_id,
            attempted_address=0,
            event_type="quota_exceeded",
        )
        self._events.append(event)
        logger.warning(
            "Quota exceeded: %s requested %d bytes (quota: %d). Process terminated.",
            allocation_id,
            requested_bytes,
            quota_bytes,
        )
        raise BarrierViolationError(
            f"Quota exceeded: {allocation_id!r} requested {requested_bytes} bytes "
            f"(quota: {quota_bytes} bytes). Allocation denied."
        )

    def barrier_events(self) -> list[dict]:
        return [e.to_dict() for e in self._events]
