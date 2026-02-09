"""Tests for HardwareMonitor - System metrics collection for thermal awareness."""

from __future__ import annotations

import pytest

from cohezion.compound.hardware_monitor import (
    HardwareMetrics,
    HardwareMonitor,
    get_hardware_monitor,
)


@pytest.fixture
def monitor() -> HardwareMonitor:
    """Create a hardware monitor instance."""
    return HardwareMonitor(enable_real_hardware=False)


class TestHardwareMetrics:
    """Test HardwareMetrics dataclass."""

    def test_initialization(self):
        """Test metrics initialization."""
        metrics = HardwareMetrics(
            cpu_temp_current=55.0,
            gpu_temp_current=65.0,
            cpu_power=20.0,
            gpu_power=15.0,
            memory_used=2.5,
            timestamp=1234567890.0,
        )
        assert metrics.cpu_temp_current == 55.0
        assert metrics.gpu_temp_current == 65.0
        assert metrics.cpu_power == 20.0
        assert metrics.gpu_power == 15.0
        assert metrics.memory_used == 2.5

    def test_gpu_clock_defaults(self):
        """Test GPU clock defaults."""
        metrics = HardwareMetrics(
            cpu_temp_current=50.0,
            gpu_temp_current=60.0,
            cpu_power=20.0,
            gpu_power=15.0,
            memory_used=2.0,
            timestamp=1234567890.0,
        )
        assert metrics.gpu_clock_mhz == 2800.0  # Default max clock
        assert metrics.gpu_max_clock_mhz == 2800.0


class TestHardwareMonitorInit:
    """Test hardware monitor initialization."""

    def test_initialization_disabled(self):
        """Test initialization with hardware disabled."""
        monitor = HardwareMonitor(enable_real_hardware=False)
        assert monitor.enable_real_hardware is False
        assert not monitor._hardware_available

    def test_initialization_enabled(self):
        """Test initialization with hardware enabled."""
        monitor = HardwareMonitor(enable_real_hardware=True)
        assert monitor.enable_real_hardware is True
        # _hardware_available depends on system, just check it's a bool

    def test_thermal_limits(self):
        """Test thermal limit constants."""
        assert HardwareMonitor.THERMAL_THROTTLE_START == 92.0
        assert HardwareMonitor.THERMAL_CRITICAL == 95.0
        assert HardwareMonitor.DEFAULT_CPU_TEMP == 55.0
        assert HardwareMonitor.DEFAULT_GPU_TEMP == 60.0


class TestGetCurrentMetrics:
    """Test metric reading."""

    def test_get_metrics_disabled_hardware(self, monitor):
        """Test getting metrics with hardware disabled."""
        metrics = monitor.get_current_metrics()

        assert isinstance(metrics, HardwareMetrics)
        assert metrics.cpu_temp_current == monitor.DEFAULT_CPU_TEMP
        assert metrics.gpu_temp_current == monitor.DEFAULT_GPU_TEMP
        assert metrics.cpu_power == monitor.DEFAULT_CPU_POWER
        assert metrics.gpu_power == monitor.DEFAULT_GPU_POWER
        assert metrics.memory_used == monitor.DEFAULT_MEMORY_USED

    def test_metrics_all_fields(self, monitor):
        """Test that metrics have all required fields."""
        metrics = monitor.get_current_metrics()

        assert hasattr(metrics, "cpu_temp_current")
        assert hasattr(metrics, "gpu_temp_current")
        assert hasattr(metrics, "cpu_power")
        assert hasattr(metrics, "gpu_power")
        assert hasattr(metrics, "memory_used")
        assert hasattr(metrics, "timestamp")
        assert hasattr(metrics, "gpu_clock_mhz")
        assert hasattr(metrics, "gpu_max_clock_mhz")

    def test_metrics_reasonable_values(self, monitor):
        """Test that metrics have reasonable values."""
        metrics = monitor.get_current_metrics()

        assert 40 <= metrics.cpu_temp_current <= 100  # 40-100°C reasonable range
        assert 50 <= metrics.gpu_temp_current <= 100  # 50-100°C reasonable
        assert 0 <= metrics.cpu_power <= 200  # 0-200W reasonable
        assert 0 <= metrics.gpu_power <= 150  # 0-150W reasonable
        assert 0 <= metrics.memory_used <= 128  # 0-128GB reasonable
        assert metrics.gpu_clock_mhz > 0
        assert metrics.gpu_max_clock_mhz > 0

    def test_multiple_calls_consistent(self, monitor):
        """Test that multiple calls return consistent defaults."""
        m1 = monitor.get_current_metrics()
        m2 = monitor.get_current_metrics()

        assert m1.cpu_temp_current == m2.cpu_temp_current
        assert m1.gpu_temp_current == m2.gpu_temp_current
        # Timestamps will differ
        assert m1.timestamp <= m2.timestamp


class TestThermalThrottling:
    """Test throttling detection."""

    def test_is_thermal_throttling_disabled(self, monitor):
        """Test throttling detection with disabled hardware."""
        throttling = monitor.is_thermal_throttling()
        assert isinstance(throttling, bool)

    def test_get_throttle_percentage_no_throttle(self, monitor):
        """Test throttle percentage when not throttled."""
        pct = monitor.get_throttle_percentage()

        assert isinstance(pct, float)
        assert 0.0 <= pct <= 100.0

    def test_throttle_percentage_bounds(self, monitor):
        """Test that throttle percentage stays in valid range."""
        for _ in range(5):
            pct = monitor.get_throttle_percentage()
            assert 0.0 <= pct <= 100.0


class TestGetStats:
    """Test statistics reporting."""

    def test_stats_structure(self, monitor):
        """Test stats has expected keys."""
        stats = monitor.get_stats()

        assert "hardware_available" in stats
        assert "current_cpu_temp_c" in stats
        assert "current_gpu_temp_c" in stats
        assert "current_cpu_power_w" in stats
        assert "current_gpu_power_w" in stats
        assert "current_memory_used_gb" in stats
        assert "gpu_clock_mhz" in stats
        assert "gpu_max_clock_mhz" in stats
        assert "thermal_throttling" in stats
        assert "throttle_percentage" in stats

    def test_stats_values_valid(self, monitor):
        """Test stats have valid values."""
        stats = monitor.get_stats()

        assert isinstance(stats["hardware_available"], bool)
        assert isinstance(stats["current_cpu_temp_c"], float)
        assert isinstance(stats["current_gpu_temp_c"], float)
        assert isinstance(stats["thermal_throttling"], bool)
        assert isinstance(stats["throttle_percentage"], float)
        assert 0.0 <= stats["throttle_percentage"] <= 100.0


class TestDefaultValues:
    """Test default fallback values."""

    def test_cpu_temp_default(self, monitor):
        """Test CPU temperature default."""
        metrics = monitor.get_current_metrics()
        assert metrics.cpu_temp_current == monitor.DEFAULT_CPU_TEMP

    def test_gpu_temp_default(self, monitor):
        """Test GPU temperature default."""
        metrics = monitor.get_current_metrics()
        assert metrics.gpu_temp_current == monitor.DEFAULT_GPU_TEMP

    def test_power_defaults(self, monitor):
        """Test power draw defaults."""
        metrics = monitor.get_current_metrics()
        assert metrics.cpu_power == monitor.DEFAULT_CPU_POWER
        assert metrics.gpu_power == monitor.DEFAULT_GPU_POWER

    def test_memory_default(self, monitor):
        """Test memory usage default."""
        metrics = monitor.get_current_metrics()
        assert metrics.memory_used == monitor.DEFAULT_MEMORY_USED


class TestSingletonFactory:
    """Test singleton factory function."""

    def test_get_singleton(self):
        """Test getting singleton instance."""
        m1 = get_hardware_monitor()
        m2 = get_hardware_monitor()

        assert m1 is m2

    def test_reset_singleton(self):
        """Test resetting singleton."""
        m1 = get_hardware_monitor()
        m2 = get_hardware_monitor(reset=True)

        assert m1 is not m2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_metrics_with_zero_clocks(self):
        """Test metrics with zero GPU clocks."""
        metrics = HardwareMetrics(
            cpu_temp_current=50.0,
            gpu_temp_current=60.0,
            cpu_power=20.0,
            gpu_power=15.0,
            memory_used=2.0,
            timestamp=1234567890.0,
            gpu_clock_mhz=0.0,
            gpu_max_clock_mhz=0.0,
        )
        assert metrics.gpu_clock_mhz == 0.0

    def test_multiple_monitor_instances(self):
        """Test creating multiple independent monitor instances."""
        m1 = HardwareMonitor(enable_real_hardware=False)
        m2 = HardwareMonitor(enable_real_hardware=False)

        # Should be different instances
        assert m1 is not m2

        # But should have same defaults
        metrics1 = m1.get_current_metrics()
        metrics2 = m2.get_current_metrics()

        assert metrics1.cpu_temp_current == metrics2.cpu_temp_current

    def test_extreme_temperatures(self):
        """Test metrics with extreme temperatures."""
        metrics = HardwareMetrics(
            cpu_temp_current=150.0,  # Way too hot
            gpu_temp_current=120.0,
            cpu_power=300.0,
            gpu_power=200.0,
            memory_used=128.0,
            timestamp=1234567890.0,
        )
        assert metrics.cpu_temp_current == 150.0
        assert metrics.gpu_temp_current == 120.0

    def test_throttling_bounds(self, monitor):
        """Test throttling percentage stays in bounds."""
        for _ in range(10):
            pct = monitor.get_throttle_percentage()
            assert 0.0 <= pct <= 100.0


class TestTemperatureMonitoring:
    """Test temperature monitoring over time."""

    def test_consecutive_reads(self, monitor):
        """Test consecutive metric reads."""
        metrics_list = [monitor.get_current_metrics() for _ in range(5)]

        # All should be HardwareMetrics
        for m in metrics_list:
            assert isinstance(m, HardwareMetrics)

        # Timestamps should increase
        for i in range(len(metrics_list) - 1):
            assert metrics_list[i].timestamp <= metrics_list[i + 1].timestamp


class TestHardwareLimits:
    """Test hardware limit constants."""

    def test_throttle_threshold(self):
        """Test throttle threshold is reasonable."""
        assert 90.0 <= HardwareMonitor.THERMAL_THROTTLE_START <= 95.0

    def test_critical_threshold(self):
        """Test critical threshold is above throttle threshold."""
        assert HardwareMonitor.THERMAL_CRITICAL > HardwareMonitor.THERMAL_THROTTLE_START

    def test_safe_default_temps(self):
        """Test default temperatures are reasonable."""
        assert 40.0 <= HardwareMonitor.DEFAULT_CPU_TEMP <= 70.0
        assert 50.0 <= HardwareMonitor.DEFAULT_GPU_TEMP <= 80.0
