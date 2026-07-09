"""SR1 tests for ResourceGuard.can_load_model — the OOM hard gate.

Per the cohezion-extend-availability skill, this method was claimed to be
landed at commit 93525db6a but was absent from the live codebase. These tests
define the contract before the implementation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.reliability.resource_guard import ResourceGuard, SystemVitals


class TestCanLoadModel:
    """can_load_model(estimated_mb) → (ok: bool, reason: str)."""

    def test_accepts_when_ram_sufficient(self):
        guard = ResourceGuard(min_ram_available_mb=16384)
        vitals = SystemVitals(
            cpu_load_1m=5.0, ram_available_mb=65536, ram_percent=50.0, swap_used_mb=0
        )
        with patch.object(guard, "get_vitals", return_value=vitals):
            ok, reason = guard.can_load_model(estimated_mb=5000)
        assert ok is True
        assert "ok" in reason.lower()

    def test_rejects_when_estimated_exceeds_available(self):
        """When RAM is above floor but below the estimate, the estimate check fires."""
        guard = ResourceGuard(min_ram_available_mb=16384)
        vitals = SystemVitals(
            cpu_load_1m=5.0, ram_available_mb=20000, ram_percent=70.0, swap_used_mb=0
        )
        with patch.object(guard, "get_vitals", return_value=vitals):
            ok, reason = guard.can_load_model(estimated_mb=50000)
        assert ok is False
        assert "50000" in reason or "insufficient" in reason.lower()

    def test_rejects_when_below_floor_even_if_estimate_small(self):
        """Loading a 100MB model when RAM is below the 16GB floor is unsafe —
        the floor exists because the OS + running services need that headroom."""
        guard = ResourceGuard(min_ram_available_mb=16384)
        vitals = SystemVitals(
            cpu_load_1m=5.0, ram_available_mb=8000, ram_percent=85.0, swap_used_mb=0
        )
        with patch.object(guard, "get_vitals", return_value=vitals):
            ok, reason = guard.can_load_model(estimated_mb=100)
        assert ok is False
        assert "floor" in reason.lower() or "8000" in reason

    def test_accepts_when_estimate_zero_and_ram_ok(self):
        """estimated_mb=0 means 'unknown size' — still gate on the RAM floor."""
        guard = ResourceGuard(min_ram_available_mb=16384)
        vitals = SystemVitals(
            cpu_load_1m=5.0, ram_available_mb=65536, ram_percent=50.0, swap_used_mb=0
        )
        with patch.object(guard, "get_vitals", return_value=vitals):
            ok, reason = guard.can_load_model(estimated_mb=0)
        assert ok is True

    def test_rejects_when_cpu_unhealthy(self):
        guard = ResourceGuard(max_cpu_load=24.0, min_ram_available_mb=16384)
        vitals = SystemVitals(
            cpu_load_1m=30.0, ram_available_mb=65536, ram_percent=50.0, swap_used_mb=0
        )
        with patch.object(guard, "get_vitals", return_value=vitals):
            ok, reason = guard.can_load_model(estimated_mb=100)
        assert ok is False
        assert "cpu" in reason.lower()

    def test_live_system_accepts_5000mb(self):
        """On the live Strix Halo with >16GB free, a 5GB model load is safe."""
        guard = ResourceGuard()
        ok, reason = guard.can_load_model(estimated_mb=5000)
        assert isinstance(ok, bool)
        assert isinstance(reason, str)


class TestRequireCanLoad:
    """require_can_load(estimated_mb) raises MemoryError on refusal."""

    def test_raises_on_insufficient_ram(self):
        guard = ResourceGuard(min_ram_available_mb=16384)
        vitals = SystemVitals(
            cpu_load_1m=5.0, ram_available_mb=4000, ram_percent=70.0, swap_used_mb=0
        )
        with patch.object(guard, "get_vitals", return_value=vitals):
            with pytest.raises(MemoryError, match=""):
                guard.require_can_load(estimated_mb=5000)

    def test_passes_on_sufficient_ram(self):
        guard = ResourceGuard(min_ram_available_mb=16384)
        vitals = SystemVitals(
            cpu_load_1m=5.0, ram_available_mb=65536, ram_percent=50.0, swap_used_mb=0
        )
        with patch.object(guard, "get_vitals", return_value=vitals):
            guard.require_can_load(estimated_mb=5000)
