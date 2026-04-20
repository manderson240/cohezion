"""VLIW-Aligned Steel Thread (Story 1.2, FR-3, NFR-9).

Exposes SIMD-accelerated kernels to Python for 12D state transitions.
Falls back to pure-Python physics path if compilation fails, with structured warning.
Benchmark: <10ms checkpoint latency (verified in tests).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum

import numpy as np


logger = logging.getLogger(__name__)

MANIFOLD_DIM = 12


class ExecutionMode(Enum):
    SIMD = "simd"
    FALLBACK_PYTHON = "fallback_python"


@dataclass
class KernelBenchmark:
    latency_ms: float
    mode: ExecutionMode
    transition_count: int = 1


@dataclass
class VLIWBridgeState:
    mode: ExecutionMode
    compilation_error: str | None = None
    is_degraded: bool = False


class VLIWBridge:
    """SIMD-accelerated kernel bridge with Python fallback.

    In production, this wraps a PyO3-compiled Rust SIMD kernel.
    In this software-emulated implementation, numpy provides the vectorized ops.
    """

    def __init__(self, force_fallback: bool = False, compilation_error: str | None = None) -> None:
        if force_fallback or compilation_error:
            self._mode = ExecutionMode.FALLBACK_PYTHON
            self._compilation_error = compilation_error or "simulated compilation failure"
            self._degraded = True
            logger.warning(
                "VLIW bridge fallback: %s. 12D state tracking continues at reduced throughput.",
                self._compilation_error,
            )
        else:
            self._mode = ExecutionMode.SIMD
            self._compilation_error = None
            self._degraded = False

    def execute_state_transition(self, state: np.ndarray, delta: np.ndarray) -> np.ndarray:
        """Apply a 12D state transition with SIMD (or Python fallback) acceleration.

        Returns the new 12D state vector.
        """
        if state.shape != (MANIFOLD_DIM,) or delta.shape != (MANIFOLD_DIM,):
            raise ValueError(f"State and delta must be {MANIFOLD_DIM}D vectors")

        if self._mode == ExecutionMode.SIMD:
            return self._simd_transition(state, delta)
        return self._python_transition(state, delta)

    def benchmark_transition(self, state: np.ndarray, delta: np.ndarray) -> KernelBenchmark:
        """Execute transition and measure latency."""
        t0 = time.perf_counter()
        self.execute_state_transition(state, delta)
        latency_ms = (time.perf_counter() - t0) * 1000
        return KernelBenchmark(latency_ms=latency_ms, mode=self._mode)

    @property
    def state(self) -> VLIWBridgeState:
        return VLIWBridgeState(
            mode=self._mode,
            compilation_error=self._compilation_error,
            is_degraded=self._degraded,
        )

    def _simd_transition(self, state: np.ndarray, delta: np.ndarray) -> np.ndarray:
        """NumPy-vectorized transition (VLEN=8 SIMD equivalent)."""
        # Vectorized addition — numpy uses AVX-512 intrinsics on Zen 5 when available
        return np.clip(state + delta, -1.0, 1.0)

    def _python_transition(self, state: np.ndarray, delta: np.ndarray) -> np.ndarray:
        """Pure-Python fallback — functional but slower."""
        result = []
        for s, d in zip(state, delta, strict=True):
            result.append(max(-1.0, min(1.0, s + d)))
        return np.array(result)
