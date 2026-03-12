"""Tests for VLIW-Aligned Steel Thread (Story 1.2)."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.vliw_bridge import ExecutionMode, VLIWBridge


class TestVLIWBridge:
    def test_simd_transition_returns_12d_state(self):
        bridge = VLIWBridge()
        state = np.zeros(12)
        delta = np.array([0.1] * 12)
        result = bridge.execute_state_transition(state, delta)
        assert result.shape == (12,)

    def test_simd_mode_by_default(self):
        bridge = VLIWBridge()
        assert bridge.state.mode == ExecutionMode.SIMD
        assert not bridge.state.is_degraded

    def test_fallback_mode_on_compilation_error(self):
        bridge = VLIWBridge(compilation_error="missing avx512 target")
        assert bridge.state.mode == ExecutionMode.FALLBACK_PYTHON
        assert bridge.state.is_degraded
        assert "avx512" in bridge.state.compilation_error

    def test_fallback_transition_functional(self):
        bridge = VLIWBridge(force_fallback=True)
        state = np.array([0.1] * 12)
        delta = np.array([0.2] * 12)
        result = bridge.execute_state_transition(state, delta)
        assert result.shape == (12,)
        assert abs(result[0] - 0.3) < 1e-9

    def test_transition_clips_to_bounds(self):
        bridge = VLIWBridge()
        state = np.array([0.9] * 12)
        delta = np.array([0.5] * 12)  # Would go to 1.4
        result = bridge.execute_state_transition(state, delta)
        assert all(v <= 1.0 for v in result)

    def test_benchmark_returns_latency(self):
        bridge = VLIWBridge()
        state = np.zeros(12)
        delta = np.array([0.01] * 12)
        bench = bridge.benchmark_transition(state, delta)
        assert bench.latency_ms >= 0.0
        assert bench.mode == ExecutionMode.SIMD

    def test_wrong_dimension_raises(self):
        bridge = VLIWBridge()
        with pytest.raises(ValueError, match="12D"):
            bridge.execute_state_transition(np.zeros(5), np.zeros(12))
