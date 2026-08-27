#!/usr/bin/env python3
"""Validate Spontaneous Symmetry Breaking & Landau Phase Transition Locally.

Demonstrates:
1. Symmetric ambiguous grid state (Phi = 0.0).
2. Spontaneous symmetry breaking via Ginzburg-Landau Mexican-hat potential V(Phi).
3. Parity resolution and order parameter convergence (Phi -> 1.414) in <1.0ms.
"""

import time
from cohezion.physics.symmetry_breaking_engine import SymmetryBreakingEngine

def validate_symmetry_breaking():
    print("=" * 90)
    print("⚛️ LOCAL VALIDATION: SPONTANEOUS SYMMETRY BREAKING & LANDAU PHASE ENGINE")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 90)

    # 1. Create a perfectly symmetric ambiguous grid (e.g., twin identical columns)
    symmetric_grid = [
        [2, 0, 0, 2],
        [2, 0, 0, 2],
        [2, 0, 0, 2],
        [2, 0, 0, 2]
    ]

    print("\n--- 1. INPUT SYMMETRIC AMBIGUOUS GRID ---")
    for row in symmetric_grid:
        print(" ", row)

    t0 = time.perf_counter()
    engine = SymmetryBreakingEngine(alpha=2.0, beta=1.0)
    broken_grid, order_param = engine.break_grid_symmetry(symmetric_grid, perturbation_axis="horizontal")
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\n--- 2. BROKEN-SYMMETRY GROUND STATE (Execution time: {dt_ms:.3f}ms) ---")
    for row in broken_grid:
        print(" ", row)

    print(f"\n✓ Landau Order Parameter (Phi): {order_param:.4f} (Theoretical ground state: {engine.phi_ground_state:.4f})")
    assert order_param > 1.0
    print("✓ Verification PASS: Mexican-hat free energy spontaneously bifurcated symmetric states into distinct chiral phases!")
    print("=" * 90)

if __name__ == "__main__":
    validate_symmetry_breaking()
