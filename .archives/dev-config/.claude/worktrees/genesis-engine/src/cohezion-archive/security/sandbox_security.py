"""Substrate Sandbox Security Verification (Story 1.7, NFR-1, Security).

Red-team verification of Memory-Mapped Barrier Isolation. Every out-of-bounds
read is blocked and logged. Over-quota allocation terminates the SLM process
and creates a structured audit event.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cohezion.security.memory_barrier import BarrierViolationError, MemoryMappedBarrier


logger = logging.getLogger(__name__)


@dataclass
class PenetrationResult:
    """Result of a single red-team probe."""

    probe_id: str
    blocked: bool
    audit_logged: bool
    physics_impact: str = "none"  # "none" | "latency_ms" | "corruption"

    def to_dict(self) -> dict:
        return {
            "probe_id": self.probe_id,
            "blocked": self.blocked,
            "audit_logged": self.audit_logged,
            "physics_impact": self.physics_impact,
        }


@dataclass
class SandboxAuditEvent:
    allocation_id: str
    event_type: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "allocation_id": self.allocation_id,
            "event_type": self.event_type,
            "detail": self.detail,
        }


class SandboxRedTeam:
    """Penetration test harness for the Memory-Mapped Barrier."""

    def __init__(self, barrier: MemoryMappedBarrier) -> None:
        self._barrier = barrier
        self._audit_events: list[SandboxAuditEvent] = []
        self._probes_run: int = 0

    def probe_out_of_bounds_read(self, allocation_id: str, out_of_bounds_address: int) -> PenetrationResult:
        """Attempt to read outside the allocation. Must be blocked and logged."""
        self._probes_run += 1
        probe_id = f"probe-{self._probes_run:04d}"
        blocked = False

        try:
            self._barrier.read(allocation_id, out_of_bounds_address)
        except BarrierViolationError as e:
            blocked = True
            self._audit_events.append(
                SandboxAuditEvent(
                    allocation_id=allocation_id,
                    event_type="out_of_bounds_read_blocked",
                    detail=str(e),
                )
            )

        return PenetrationResult(
            probe_id=probe_id,
            blocked=blocked,
            audit_logged=blocked,
            physics_impact="none",
        )

    def probe_quota_overflow(self, allocation_id: str, requested_bytes: int, quota_bytes: int) -> PenetrationResult:
        """Attempt over-quota allocation. SLM must be denied and terminated."""
        self._probes_run += 1
        probe_id = f"probe-{self._probes_run:04d}"
        blocked = False

        try:
            self._barrier.deny_over_quota_allocation(allocation_id, requested_bytes, quota_bytes)
        except BarrierViolationError as e:
            blocked = True
            self._audit_events.append(
                SandboxAuditEvent(
                    allocation_id=allocation_id,
                    event_type="quota_exceeded_process_terminated",
                    detail=str(e),
                )
            )

        return PenetrationResult(
            probe_id=probe_id,
            blocked=blocked,
            audit_logged=blocked,
        )

    def run_full_pentest(self, allocation_id: str, base_address: int, size_bytes: int) -> list[PenetrationResult]:
        """Run a comprehensive pentest: multiple out-of-bounds probes + quota overflow."""
        results = []

        # Before address
        results.append(self.probe_out_of_bounds_read(allocation_id, base_address - 1))

        # After address
        results.append(self.probe_out_of_bounds_read(allocation_id, base_address + size_bytes))

        # Far out of bounds
        results.append(self.probe_out_of_bounds_read(allocation_id, 0xDEADBEEF))

        # Quota overflow
        results.append(self.probe_quota_overflow(allocation_id, size_bytes * 10, size_bytes))

        return results

    def all_blocked(self) -> bool:
        return all(self._barrier.barrier_events())

    def audit_events(self) -> list[dict]:
        return [e.to_dict() for e in self._audit_events]

    @property
    def probes_run(self) -> int:
        return self._probes_run
