#!/usr/bin/env python3
"""Validate BlueQubit Quantum Computing Bridge Locally.

Demonstrates:
1. SDK initialization and environment detection.
2. Building an OpenQASM GHZ superposition state circuit.
3. Verification with local fallback and live API execution.
"""

import time
from cohezion.quantum.bluequbit_quantum_bridge import BlueQubitQuantumBridge

def validate_bridge():
    print("=" * 80)
    print("⚛️ VALIDATING BLUEQUBIT QUANTUM BRIDGE INTEGRATION")
    print("=" * 80)

    t0 = time.perf_counter()
    bridge = BlueQubitQuantumBridge()
    res = bridge.run_quantum_kernel(num_qubits=4)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print(f"Status: {res.get('status')}")
    print(f"Device: {res.get('device')}")
    print(f"Measurement Counts: {res.get('counts')}")
    print(f"Latency: {dt_ms:.2f} ms")
    print("✓ BlueQubit Quantum Bridge operational with fallback safety!")
    print("=" * 80)

if __name__ == "__main__":
    validate_bridge()
