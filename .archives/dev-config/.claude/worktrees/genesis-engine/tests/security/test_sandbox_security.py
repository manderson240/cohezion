"""Tests for Substrate Sandbox Security Verification (Story 1.7)."""

from __future__ import annotations

from cohezion.security.memory_barrier import MemoryMappedBarrier
from cohezion.security.sandbox_security import SandboxRedTeam


class TestSandboxRedTeam:
    def _setup(self):
        barrier = MemoryMappedBarrier()
        alloc = barrier.allocate("target", size_bytes=65536)
        redteam = SandboxRedTeam(barrier)
        return redteam, alloc

    def test_out_of_bounds_probe_blocked(self):
        redteam, alloc = self._setup()
        result = redteam.probe_out_of_bounds_read("target", alloc.end_address + 100)
        assert result.blocked is True
        assert result.audit_logged is True
        assert result.physics_impact == "none"

    def test_quota_overflow_probe_blocked(self):
        redteam, alloc = self._setup()
        result = redteam.probe_quota_overflow("target", alloc.size_bytes * 10, alloc.size_bytes)
        assert result.blocked is True
        assert result.audit_logged is True

    def test_full_pentest_all_blocked(self):
        redteam, alloc = self._setup()
        results = redteam.run_full_pentest("target", alloc.base_address, alloc.size_bytes)
        assert all(r.blocked for r in results)

    def test_audit_events_accumulated(self):
        redteam, alloc = self._setup()
        redteam.probe_out_of_bounds_read("target", alloc.end_address)
        redteam.probe_out_of_bounds_read("target", alloc.end_address + 1)
        events = redteam.audit_events()
        assert len(events) == 2

    def test_probes_run_counted(self):
        redteam, alloc = self._setup()
        redteam.probe_out_of_bounds_read("target", alloc.end_address)
        assert redteam.probes_run == 1

    def test_physics_substrate_unimpacted(self):
        redteam, alloc = self._setup()
        results = redteam.run_full_pentest("target", alloc.base_address, alloc.size_bytes)
        for r in results:
            assert r.physics_impact == "none"
