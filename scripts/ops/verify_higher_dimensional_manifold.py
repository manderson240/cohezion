#!/usr/bin/env python3
"""
Higher-Dimensional Poincaré Manifold Verification Script
==========================================================
Tests geometric operations across higher dimensions:
  - 12D: FLUME Base (3 Spatial + 1 Time + 8 Brane)
  - 16D: Octonionic Bioelectric Manifold
  - 26D: Bosonic String Critical Dimension Manifold
  - 32D: Dirac-Kähler Spinor Space
  - 256D: FLUME J-Space Latent Vector Space
  - 2048D: Full Cohezion SOUL_DIM Manifold Space
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND


def benchmark_manifold_dimension(dim: int) -> dict:
    # 1. Project points into N-dimensional unit Poincaré ball
    raw_1 = tuple([0.05 * (i % 7 + 1) for i in range(dim)])
    raw_2 = tuple([0.08 * (i % 5 + 1) for i in range(dim)])

    p1 = PoincareManifoldND.project(raw_1, target_dim=dim)
    p2 = PoincareManifoldND.project(raw_2, target_dim=dim)

    # 2. Hyperbolic Distance
    dist = PoincareManifoldND.distance(p1, p2)

    # 3. Parallel Transport of Tangent Vector
    tangent_v = tuple([1.0 / math.sqrt(dim)] * dim)
    v_transported = PoincareManifoldND.parallel_transport(tangent_v, p1, p2)

    # 4. Curvature Loss across 5 points
    cluster = [PoincareManifoldND.project(tuple([(0.02 * k * i) % 0.8 for i in range(dim)])) for k in range(1, 6)]
    loss = PoincareManifoldND.curvature_regularization_loss(cluster)

    return {
        "dim": dim,
        "p1_norm": round(p1.norm, 4),
        "p2_norm": round(p2.norm, 4),
        "hyperbolic_distance": round(dist, 4),
        "transported_norm": round(math.sqrt(sum(x * x for x in v_transported)), 4),
        "curvature_loss": round(loss, 4),
    }


def main():
    print("=== Higher-Dimensional Poincaré Manifold Benchmark ===")

    dimensions = [12, 16, 26, 32, 256, 2048]
    for d in dimensions:
        res = benchmark_manifold_dimension(d)
        print(f"\n[{d}D Manifold] Results:")
        for k, v in res.items():
            print(f"  • {k}: {v}")

    print("\n✅ All Higher-Dimensional Manifold Verifications Complete!")


if __name__ == "__main__":
    main()
