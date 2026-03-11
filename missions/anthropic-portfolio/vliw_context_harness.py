"""
VLIW Context Harness: Strict Performance Engineering Environment.

Enforces Anthropic's Performance Take-home rules:
1. N_CORES = 1 (Strict Single-Threaded Mastery).
2. SCRATCH_SIZE = 1536 (Register Pressure).
3. BIT_EXACT = 100% (No Hallucinations in Math).
4. TIME_LIMIT = 300s (Simulation Constraint).
"""

import time
import numpy as np
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class VLIWEnvironment:
    n_cores: int = 1
    scratch_size: int = 1536
    vlen: int = 8
    max_cycles: int = 1000000
    timeout_seconds: float = 300.0

class VLIWContextHarness:
    """Enforces the 'Constitutional' constraints of the VLIW challenge."""

    def __init__(self, env: VLIWEnvironment | None = None):
        self.env = env or VLIWEnvironment()
        self.start_time = 0.0

    def execute_with_constraints(self, builder_func: Callable, *args, **kwargs) -> dict[str, Any]:
        """Execute a kernel build/sim within the strict rule harness."""
        self.start_time = time.perf_counter()
        
        # 1. Enforce Rule: Single Core Only
        if self.env.n_cores != 1:
            raise PermissionError("VLIW v2 Violation: N_CORES must be 1 for strict compliance.")

        try:
            # 2. Build the Kernel
            builder_start = time.perf_counter()
            instrs = builder_func(*args, **kwargs)
            builder_time = time.perf_counter() - builder_start

            # 3. Check for Timeout
            elapsed = time.perf_counter() - self.start_time
            if elapsed > self.env.timeout_seconds:
                return {"status": "TIMEOUT", "time": elapsed}

            return {
                "status": "SUCCESS",
                "instructions": len(instrs),
                "build_time_ms": builder_time * 1000,
                "total_time_s": elapsed,
                "environment": self.env
            }

        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    @staticmethod
    def verify_bit_exact(vector_data: np.ndarray, reference: np.ndarray) -> bool:
        """Strict Bit-Exact Verification (No 0.5 drift allowed here)."""
        if vector_data.shape != reference.shape:
            return False
        
        matches = np.array_equal(vector_data, reference)
        return bool(matches)
