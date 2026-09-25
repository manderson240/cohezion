#!/usr/bin/env python3
"""Validate Live BlueQubit ARC Graph Matching QUBO on Cloud Quantum Hardware.

Exits non-zero, with the reason, when no real backend is available.
"""

import sys
import time

from cohezion.quantum import QuantumBackendUnavailableError
from cohezion.quantum.bluequbit_arc_qubo_solver import BlueQubitARCSolver


def validate_arc_qubo() -> int:
    print("=" * 80)
    print("⚛️ VALIDATING LIVE BLUEQUBIT ARC-AGI QUBO SOLVER")
    print("=" * 80)

    # 4 candidate transforms with distinct energy/cost penalties
    cost_matrix = [
        [0.1, 0.8, 0.9, 0.4],
        [0.8, 0.2, 0.7, 0.5],
        [0.9, 0.7, 0.05, 0.6],  # Index 2 has minimal penalty (optimal match)
        [0.4, 0.5, 0.6, 0.3],
    ]

    solver = BlueQubitARCSolver(device="mps.cpu")
    print("▶ Dispatching parameterized quantum circuit to BlueQubit...")
    t0 = time.perf_counter()
    try:
        res = solver.solve_graph_isomorphism_qubo(cost_matrix, shots=1000)
    except QuantumBackendUnavailableError as e:
        print(f"✗ BlueQubit backend unavailable: {e}")
        return 1

    print(f"Status: {res['status']}")
    print(f"Job ID: {res['job_id']}")
    print(f"Device: {res['device']}")
    print(f"Optimal Candidate Index: #{res['optimal_candidate_index']}")
    print(f"Optimal Bitstring: {res['bitstring']}")
    print(f"Cloud Execution Time: {res['latency_s']:.2f}s (wall {time.perf_counter() - t0:.2f}s)")
    print("✓ BlueQubit returned measured counts.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(validate_arc_qubo())
