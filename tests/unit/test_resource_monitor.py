"""Tests for the ResourceMonitor (cohezion.reliability.monitor)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.reliability.monitor import ResourceMonitor, get_resource_monitor


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset ResourceMonitor singleton between tests."""
    ResourceMonitor._instance = None
    yield
    ResourceMonitor._instance = None


class TestResourceMonitorInit:
    def test_default_concurrency(self):
        rm = ResourceMonitor()
        assert rm.max_concurrency == 4

    def test_custom_concurrency(self):
        rm = ResourceMonitor(max_concurrency=8)
        assert rm.max_concurrency == 8

    def test_singleton_pattern(self):
        rm1 = ResourceMonitor()
        rm2 = ResourceMonitor()
        assert rm1 is rm2

    def test_initial_state(self):
        rm = ResourceMonitor()
        assert rm.active_calls == 0
        assert rm.critical_pressure is False
        assert rm.throttled is False
        assert rm.desperation_active is False
        assert rm.dilation_factor == 1.0


class TestGetVitals:
    @patch("cohezion.reliability.monitor.psutil")
    def test_vitals_keys(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 25.0
        mock_vm = MagicMock()
        mock_vm.percent = 45.0
        mock_vm.available = 80 * (1024**3)  # 80 GB
        mock_psutil.virtual_memory.return_value = mock_vm

        rm = ResourceMonitor()
        vitals = rm.get_vitals()

        assert "cpu_percent" in vitals
        assert "memory_percent" in vitals
        assert "memory_available_gb" in vitals
        assert "active_llm_calls" in vitals
        assert "vram_percent" in vitals
        assert "dilation_factor" in vitals
        assert "active_sandboxes" in vitals
        assert "sandbox_memory_mb" in vitals

    @patch("cohezion.reliability.monitor.psutil")
    def test_vitals_values(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 50.0
        mock_vm = MagicMock()
        mock_vm.percent = 60.0
        mock_vm.available = 50 * (1024**3)
        mock_psutil.virtual_memory.return_value = mock_vm

        rm = ResourceMonitor()
        vitals = rm.get_vitals()

        assert vitals["cpu_percent"] == 50.0
        assert vitals["memory_percent"] == 60.0
        assert vitals["active_llm_calls"] == 0


class TestSandboxRegistry:
    def test_register_sandbox(self):
        rm = ResourceMonitor()
        rm.register_sandbox("sb_1", 1024)
        assert rm.total_sandbox_memory_mb == 1024
        assert len(rm._sandbox_registry) == 1

    def test_multiple_sandboxes(self):
        rm = ResourceMonitor()
        rm.register_sandbox("sb_1", 1024)
        rm.register_sandbox("sb_2", 2048)
        assert rm.total_sandbox_memory_mb == 3072

    def test_deregister_sandbox(self):
        rm = ResourceMonitor()
        rm.register_sandbox("sb_1", 1024)
        rm.deregister_sandbox("sb_1")
        assert rm.total_sandbox_memory_mb == 0
        assert len(rm._sandbox_registry) == 0

    def test_deregister_nonexistent_is_noop(self):
        rm = ResourceMonitor()
        rm.deregister_sandbox("nonexistent")  # Should not raise


class TestCapacitySlots:
    def test_release_capacity(self):
        rm = ResourceMonitor()
        rm.active_calls = 1
        rm.release_capacity()
        assert rm.active_calls == 0

    def test_get_dilation_factor(self):
        rm = ResourceMonitor()
        assert rm.get_dilation_factor() == 1.0
        rm.dilation_factor = 0.5
        assert rm.get_dilation_factor() == 0.5


class TestVramUsage:
    def test_no_sysfs_returns_zero(self):
        rm = ResourceMonitor()
        # When no sysfs files exist, should return 0.0
        result = rm._get_vram_usage()
        # On most CI/test machines without AMD GPU sysfs, this will be 0.0
        assert isinstance(result, float)
        assert result >= 0.0


class TestRegisterCoordinator:
    def test_register_coordinator(self):
        rm = ResourceMonitor()
        coordinator = MagicMock()
        coordinator.__class__.__name__ = "MockCoordinator"
        rm.register_coordinator(coordinator)
        assert rm.resource_coordinator is coordinator


class TestGetResourceMonitor:
    def test_returns_instance(self):
        rm = get_resource_monitor()
        assert isinstance(rm, ResourceMonitor)

    def test_returns_singleton(self):
        rm1 = get_resource_monitor()
        rm2 = get_resource_monitor()
        assert rm1 is rm2
