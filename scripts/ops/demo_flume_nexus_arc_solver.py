#!/usr/bin/env python3
"""Live FLUME 12D Manifold & Quadrature Nexus ARC Solver Demonstration."""

import time
from cohezion.competitions.arc.nexus_manifold_solver import QuadratureNexusEncoder, OuroborosFeedbackEngine
from cohezion.competitions.arc.dsl_synthesizer import DSL_PRIMITIVES

def main():
    print("\n" + "=" * 95)
    print("🌌 COHEZION FLUME & QUADRATURE NEXUS MANIFOLD ARC SOLVER")
    print("=" * 95)

    sample_grid = [
        [1, 1, 0, 0],
        [1, 2, 0, 0],
        [0, 0, 3, 3],
        [0, 0, 3, 3]
    ]

    # 1. Encode into FLUME 12D Manifold State Vector
    encoder = QuadratureNexusEncoder()
    t0 = time.perf_counter()
    flume_12d = encoder.encode_grid(sample_grid)
    dt_enc = (time.perf_counter() - t0) * 1000.0

    print(f"• FLUME 12D State Vector (Encoded in {dt_enc:.3f} ms):")
    print(f"  ├─ Spatial Centroid (x, y, Area) : ({flume_12d.x}, {flume_12d.y}, {flume_12d.z_area})")
    print(f"  ├─ Time / Shannon Entropy        : {flume_12d.t_entropy} bits/cell")
    print(f"  ├─ Brane D4 Symmetry Invariant   : {flume_12d.brane_d4_symmetry}")
    print(f"  ├─ Brane Color Diversity         : {flume_12d.brane_color_diversity}")
    print(f"  └─ Quadrature HIHO 0.5 Coherence : {flume_12d.brane_quadrature_coherence}")

    # 2. Run Ouroboros Closed-Loop Solver
    engine = OuroborosFeedbackEngine(DSL_PRIMITIVES)
    task = {
        "train": [
            {"input": [[1, 2], [3, 4]], "output": [[3, 1], [4, 2]]}
        ],
        "test": [{"input": [[5, 6], [7, 8]]}]
    }
    t1 = time.perf_counter()
    res = engine.solve_with_nexus_guidance(task)
    dt_solve = (time.perf_counter() - t1) * 1000.0

    print(f"\n• Ouroboros Feedback Synthesis Result: {res} in {dt_solve:.3f} ms")
    assert res == [[7, 5], [8, 6]]

    print("\n" + "=" * 95)
    print("🎉 FLUME, QUADRATURE NEXUS & OUROBOROS ENGINES FULLY INTEGRATED!")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    main()
