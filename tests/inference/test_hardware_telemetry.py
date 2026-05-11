"""Unit tests for hardware_telemetry — AMD Strix Halo silicon utilization."""

from __future__ import annotations

import time

import pytest

from cohezion.inference.hardware_telemetry import (
    ComputeBackend,
    HardwareSnapshot,
    HardwareTelemetry,
    UtilizationProfile,
)


# ── ComputeBackend enum ───────────────────────────────────────────────────────


class TestComputeBackend:
    def test_all_strix_halo_backends_exist(self):
        """Verify all AMD Strix Halo compute backends are enumerated."""
        assert ComputeBackend.XDNA2_NPU is not None
        assert ComputeBackend.VULKAN_GPU is not None
        assert ComputeBackend.ZEN5_CPU is not None

    def test_backend_values_are_strings(self):
        for backend in ComputeBackend:
            assert isinstance(backend.value, str)


# ── HardwareSnapshot dataclass ────────────────────────────────────────────────


class TestHardwareSnapshot:
    def test_snapshot_defaults(self):
        snap = HardwareSnapshot(
            timestamp=time.time(),
            backend=ComputeBackend.XDNA2_NPU,
        )
        assert snap.utilization_pct == 0.0
        assert snap.memory_used_mb == 0
        assert snap.throttling is False

    def test_snapshot_with_values(self):
        snap = HardwareSnapshot(
            timestamp=time.time(),
            backend=ComputeBackend.VULKAN_GPU,
            utilization_pct=75.0,
            memory_used_mb=4096,
            temperature_c=65.0,
            throttling=False,
        )
        assert snap.utilization_pct == 75.0
        assert snap.memory_used_mb == 4096
        assert snap.temperature_c == 65.0


# ── UtilizationProfile ────────────────────────────────────────────────────────


class TestUtilizationProfile:
    def test_profile_defaults(self):
        p = UtilizationProfile(backend=ComputeBackend.XDNA2_NPU)
        assert p.avg_utilization == 0.0
        assert p.peak_utilization == 0.0
        assert len(p.snapshots) == 0

    def test_tokens_per_watt_efficiency_metric(self):
        """tokens_per_watt tracks NPU energy efficiency."""
        p = UtilizationProfile(
            backend=ComputeBackend.XDNA2_NPU,
            tokens_per_watt=15.0,  # NPU: ~15 tokens/watt
        )
        assert p.tokens_per_watt == 15.0


# ── HardwareTelemetry ─────────────────────────────────────────────────────────


class TestHardwareTelemetry:
    def test_instantiation_for_each_backend(self):
        """Telemetry collector can be created for each backend."""
        for backend in ComputeBackend:
            t = HardwareTelemetry(backend)
            assert t.backend == backend
            assert isinstance(t.snapshots, list)

    def test_start_records_start_time(self):
        t = HardwareTelemetry(ComputeBackend.ZEN5_CPU)
        assert t.start_time is None
        t.start()
        assert t.start_time is not None

    def test_start_time_is_monotonic(self):
        t = HardwareTelemetry(ComputeBackend.ZEN5_CPU)
        before = time.monotonic()
        t.start()
        after = time.monotonic()
        assert before <= t.start_time <= after + 0.1

    def test_tool_detection_returns_bool(self):
        """Tool detection always returns True/False (never raises)."""
        t = HardwareTelemetry(ComputeBackend.XDNA2_NPU)
        assert isinstance(t.has_rocm_smi, bool)
        assert isinstance(t.has_flm, bool)
        assert isinstance(t.has_perf, bool)

    def test_flm_available_for_npu(self):
        """FLM should be available on Strix Halo (N1 invariant: NPU is live)."""
        t = HardwareTelemetry(ComputeBackend.XDNA2_NPU)
        # On this system (AMD Strix Halo with XDNA2), FLM should be installed
        # This is a live system test — gracefully skips on other hardware
        if not t.has_flm:
            pytest.skip("FLM not installed — not on Strix Halo hardware")
        assert t.has_flm is True
