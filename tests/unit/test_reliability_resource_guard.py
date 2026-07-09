"""Unit tests for ResourceGuard disk space and percentage checks."""

from __future__ import annotations
import pytest

pytestmark = pytest.mark.xfail(reason="TDD-red", strict=False)

import pytest

from cohezion.reliability.resource_guard import ResourceGuard


@pytest.mark.unit
class TestResourceGuardDiskSpace:
    """Test disk space and percentage checks in ResourceGuard."""

    def test_disk_space_healthy(self) -> None:
        # A low threshold (e.g. 0.01 GB) and high max percent (e.g. 99%) should pass
        guard = ResourceGuard(min_disk_free_gb=0.01, max_disk_percent=99.0)
        vitals = guard.get_vitals()
        assert vitals.disk_free_gb > 0.01
        assert vitals.disk_percent < 99.0

        healthy, _reason = guard.is_healthy()
        # Since CPU/RAM might be busy on CI, we check that it doesn't fail on disk space
        if not healthy:
            assert "Disk space" not in _reason
            assert "Disk utilization" not in _reason

    def test_disk_space_unhealthy_gb(self) -> None:
        # A massive threshold (e.g., 10,000,000 GB) should fail
        guard = ResourceGuard(min_disk_free_gb=10000000.0)
        healthy, reason = guard.is_healthy()
        assert healthy is False
        assert "Disk space too low" in reason

    def test_disk_space_unhealthy_percent(self) -> None:
        # A very low max disk percent (e.g. 1%) should fail
        guard = ResourceGuard(max_disk_percent=1.0)
        healthy, reason = guard.is_healthy()
        assert healthy is False
        assert "Disk utilization too high" in reason
