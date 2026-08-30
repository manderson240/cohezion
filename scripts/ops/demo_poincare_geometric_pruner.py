#!/usr/bin/env python3
"""Live Demonstration of Poincaré Hyperbolic Geometric Correspondence Pruning."""

import time
import numpy as np
from cohezion.competitions.arc.poincare_geometric_pruner import PoincareGeometricPruner
from cohezion.competitions.arc.nexus_manifold_solver import QuadratureNexusEncoder

def main():
    print("\n" + "=" * 95)
    print("🌐 COHEZION POINCARÉ HYPERBOLIC GEOMETRIC CORRESPONDENCE PRUNER")
    print("=" * 95)

    pruner = PoincareGeometricPruner()
    encoder = QuadratureNexusEncoder()

    target_grid = [
        [1, 1, 0],
        [1, 2, 0],
        [0, 0, 3]
    ]
    target_manifold = encoder.encode_grid(target_grid)

    candidate_good = [
        [1, 1, 0],
        [1, 2, 0],
        [0, 0, 3]
    ]
    candidate_far = [
        [8, 8, 8],
        [8, 8, 8],
        [8, 8, 8]
    ]

    t0 = time.perf_counter()
    dist_close = pruner.evaluate_candidate_geodesic(candidate_good, target_manifold)
    dist_far = pruner.evaluate_candidate_geodesic(candidate_far, target_manifold)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print(f"• Exact Match Hyperbolic Distance d_P(u, v) : {dist_close:.6f} (Zero Geodesic Error)")
    print(f"• Divergent Grid Hyperbolic Distance d_P(u, v): {dist_far:.6f} (High Hyperbolic Curvature)")
    print(f"• Evaluated Hyperbolic Manifold Distance in   : {dt_ms:.3f} ms")

    assert dist_close < 1e-4
    assert dist_far > 0.5

    print("\n" + "=" * 95)
    print("🎉 POINCARÉ HYPERBOLIC GEOMETRIC CORRESPONDENCE PROVEN OPERATIONAL!")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    main()
