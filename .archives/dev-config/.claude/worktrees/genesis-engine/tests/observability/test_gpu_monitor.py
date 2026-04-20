"""Tests for GPU monitoring and thermal profiling."""

import time
from unittest.mock import patch

import pytest

from cohezion.observability.gpu_monitor import GPUMetrics, GPUMonitor


@pytest.fixture
def gpu_monitor():
    """Create GPU monitor for testing."""
    return GPUMonitor()


class TestGPUMonitor:
    """Test GPUMonitor basic functionality."""

    def test_initialization(self, gpu_monitor):
        """Test monitor initialization."""
        assert gpu_monitor._is_measuring is False
        assert len(gpu_monitor._snapshots) == 0

    def test_start_stop_measurement(self, gpu_monitor):
        """Test starting and stopping measurement."""
        assert gpu_monitor._is_measuring is False

        gpu_monitor.start_measurement()
        assert gpu_monitor._is_measuring is True
        assert gpu_monitor._start_time is not None

        gpu_monitor.stop_measurement()
        assert gpu_monitor._is_measuring is False

    def test_collect_snapshot_when_not_measuring(self, gpu_monitor):
        """Test that collecting when not measuring returns None."""
        result = gpu_monitor.collect_snapshot()
        assert result is None

    @patch("cohezion.observability.gpu_monitor.GPUMonitor._read_gpu_metrics")
    def test_collect_snapshot_when_measuring(self, mock_read, gpu_monitor):
        """Test snapshot collection while measuring."""
        # Mock metrics
        mock_metrics = GPUMetrics(
            timestamp=time.time(),
            gpu_load=45.0,
            gpu_mem_used=256.0,
            gtt_mem_used=1024.0,
            sclk=400.0,
            mclk=667.0,
            temperature=52.0,
            throttle_status="none",
        )
        mock_read.return_value = mock_metrics

        gpu_monitor.start_measurement()
        result = gpu_monitor.collect_snapshot()

        assert result is not None
        assert result.gpu_load == 45.0
        assert len(gpu_monitor._snapshots) == 1

    def test_get_statistics_empty(self, gpu_monitor):
        """Test statistics with no snapshots."""
        stats = gpu_monitor.get_statistics()
        assert stats["avg_gpu_load"] == 0.0
        assert stats["peak_gpu_load"] == 0.0
        assert stats["avg_temperature"] == 0.0
        assert stats["peak_temperature"] == 0.0
        assert stats["thermal_throttled"] is False

    def test_get_statistics_with_snapshots(self, gpu_monitor):
        """Test statistics with multiple snapshots."""
        gpu_monitor._start_time = time.time()
        gpu_monitor._is_measuring = True

        # Add snapshots
        for i in range(5):
            gpu_monitor._snapshots.append(
                GPUMetrics(
                    timestamp=time.time(),
                    gpu_load=20.0 + i * 10,  # 20, 30, 40, 50, 60
                    gpu_mem_used=256.0,
                    gtt_mem_used=1024.0,
                    sclk=400.0,
                    mclk=667.0,
                    temperature=50.0 + i * 2,  # 50, 52, 54, 56, 58
                    throttle_status="none",
                )
            )

        stats = gpu_monitor.get_statistics()

        assert stats["num_snapshots"] == 5
        assert stats["avg_gpu_load"] == pytest.approx(40.0, rel=1e-1)
        assert stats["peak_gpu_load"] == 60.0
        assert stats["avg_temperature"] == pytest.approx(54.0, rel=1e-1)
        assert stats["peak_temperature"] == 58.0
        assert stats["thermal_throttled"] is False

    def test_get_statistics_with_throttle(self, gpu_monitor):
        """Test statistics when thermal throttling detected."""
        gpu_monitor._start_time = time.time()
        gpu_monitor._is_measuring = True

        # Add snapshots, last one throttled
        for i in range(3):
            throttle = "thermal" if i == 2 else "none"
            gpu_monitor._snapshots.append(
                GPUMetrics(
                    timestamp=time.time(),
                    gpu_load=50.0,
                    gpu_mem_used=256.0,
                    gtt_mem_used=1024.0,
                    sclk=400.0,
                    mclk=667.0,
                    temperature=50.0 + i * 10,
                    throttle_status=throttle,
                )
            )

        stats = gpu_monitor.get_statistics()
        assert stats["thermal_throttled"] is True


class TestGPUMetricsParser:
    """Test GPU metrics parsing from pm_info."""

    def test_parse_gpu_load(self):
        """Test GPU load extraction."""
        pm_info = "GPU Load: 45%\nOther metrics..."
        load = GPUMonitor._parse_gpu_load(pm_info)
        assert load == 45.0

    def test_parse_gpu_load_zero(self):
        """Test GPU load when idle."""
        pm_info = "GPU Load: 0%\nOther metrics..."
        load = GPUMonitor._parse_gpu_load(pm_info)
        assert load == 0.0

    def test_parse_gpu_load_missing(self):
        """Test GPU load when not present."""
        pm_info = "Other metrics without GPU Load..."
        load = GPUMonitor._parse_gpu_load(pm_info)
        assert load == 0.0

    def test_parse_temperature(self):
        """Test temperature extraction."""
        pm_info = "Temperature: 52 C\nOther metrics..."
        temp = GPUMonitor._parse_temperature(pm_info)
        assert temp == 52.0

    def test_parse_temperature_unicode(self):
        """Test temperature with Unicode degree symbol."""
        pm_info = "Temperature: 52 °C\nOther metrics..."
        temp = GPUMonitor._parse_temperature(pm_info)
        assert temp == 52.0

    def test_parse_temperature_missing(self):
        """Test temperature when not present."""
        pm_info = "Other metrics without temperature..."
        temp = GPUMonitor._parse_temperature(pm_info)
        assert temp == 0.0

    def test_parse_clocks(self):
        """Test GPU and memory clock extraction."""
        pm_info = "SCLK: 400 Mhz\nMCLK: 667 Mhz\nOther..."
        sclk, mclk = GPUMonitor._parse_clocks(pm_info)
        assert sclk == 400.0
        assert mclk == 667.0

    def test_parse_clocks_high(self):
        """Test high clock frequencies."""
        pm_info = "SCLK: 2700 Mhz\nMCLK: 1100 Mhz\nOther..."
        sclk, mclk = GPUMonitor._parse_clocks(pm_info)
        assert sclk == 2700.0
        assert mclk == 1100.0

    def test_parse_clocks_partial(self):
        """Test when only one clock present."""
        pm_info = "SCLK: 400 Mhz\nOther metrics..."
        sclk, mclk = GPUMonitor._parse_clocks(pm_info)
        assert sclk == 400.0
        assert mclk == 0.0

    def test_parse_memory(self):
        """Test GPU and GTT memory extraction."""
        pm_info = "VRAM: 256 MB\nGTT: 2048 MB\nOther..."
        gpu_mem, gtt_mem = GPUMonitor._parse_memory(pm_info)
        assert gpu_mem == 256.0
        assert gtt_mem == 2048.0

    def test_parse_memory_large(self):
        """Test large memory amounts."""
        pm_info = "VRAM: 4096 MB\nGTT: 131072 MB\nOther..."
        gpu_mem, gtt_mem = GPUMonitor._parse_memory(pm_info)
        assert gpu_mem == 4096.0
        assert gtt_mem == 131072.0

    def test_parse_throttle_status_none(self):
        """Test throttle status when none."""
        pm_info = "GPU Load: 45%\nNo throttle info..."
        status = GPUMonitor._parse_throttle_status(pm_info)
        assert status == "none"

    def test_parse_throttle_status_thermal(self):
        """Test thermal throttle detection."""
        pm_info = "GPU Load: 95%\nThermal throttle: active\nOther..."
        status = GPUMonitor._parse_throttle_status(pm_info)
        assert status == "thermal"

    def test_parse_throttle_status_power(self):
        """Test power throttle detection."""
        pm_info = "GPU Load: 99%\nPower throttle: active\nOther..."
        status = GPUMonitor._parse_throttle_status(pm_info)
        assert status == "power"


class TestGPUMetrics:
    """Test GPUMetrics dataclass."""

    def test_creation(self):
        """Test creating GPU metrics."""
        metrics = GPUMetrics(
            timestamp=time.time(),
            gpu_load=45.0,
            gpu_mem_used=256.0,
            gtt_mem_used=1024.0,
            sclk=400.0,
            mclk=667.0,
            temperature=52.0,
            throttle_status="none",
        )
        assert metrics.gpu_load == 45.0
        assert metrics.temperature == 52.0
        assert metrics.throttle_status == "none"

    def test_creation_thermal_throttle(self):
        """Test metrics with thermal throttle."""
        metrics = GPUMetrics(
            timestamp=time.time(),
            gpu_load=99.0,
            gpu_mem_used=4096.0,
            gtt_mem_used=65536.0,
            sclk=2700.0,
            mclk=1100.0,
            temperature=85.0,
            throttle_status="thermal",
        )
        assert metrics.throttle_status == "thermal"
        assert metrics.temperature == 85.0
