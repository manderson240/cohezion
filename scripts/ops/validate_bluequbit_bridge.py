#!/usr/bin/env python3
"""Validate the BlueQubit Quantum Computing Bridge against the live API.

Demonstrates:
1. SDK initialization and environment detection.
2. Building an OpenQASM GHZ superposition state circuit.
3. Live API execution. There is no local fallback: without a real backend this
   script reports why and exits non-zero rather than printing placeholder counts.
"""

import sys
import time

from cohezion.quantum import QuantumBackendUnavailableError
from cohezion.quantum.bluequbit_quantum_bridge import BlueQubitQuantumBridge


def validate_bridge() -> int:
    print("=" * 80)
    print("⚛️ VALIDATING BLUEQUBIT QUANTUM BRIDGE INTEGRATION")
    print("=" * 80)

    t0 = time.perf_counter()
    bridge = BlueQubitQuantumBridge()
    try:
        res = bridge.run_quantum_kernel(num_qubits=4)
    except QuantumBackendUnavailableError as e:
        print(f"✗ BlueQubit backend unavailable: {e}")
        return 1
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print(f"Status: {res['status']}")
    print(f"Job ID: {res['job_id']}")
    print(f"Device: {res['device']}")
    print(f"Measurement Counts: {res['counts']}")
    print(f"Latency: {dt_ms:.2f} ms")
    print("✓ BlueQubit Quantum Bridge returned measured counts.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(validate_bridge())
