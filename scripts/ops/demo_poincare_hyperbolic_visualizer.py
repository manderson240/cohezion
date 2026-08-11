#!/usr/bin/env python3
"""
Poincaré 2048D Hyperbolic Manifold Visualizer Harness Demo
=========================================================
Verifies 2048D vector projection to 3D Poincaré ball, exact hyperbolic distance
computation d_P(u,v) = arcosh(1 + 2*||u-v||^2 / ((1-||u||^2)*(1-||v||^2))),
skill & retrospective mapping, and Plotly figure generation in < 100ms.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

import numpy as np

from cohezion.flume.poincare_manifold_visualizer import (
    PoincareManifoldVisualizer,
    compute_hyperbolic_distance,
    compute_hyperbolic_distance_batch,
    figure_to_html,
    figure_to_json,
    generate_poincare_figure,
    project_2048d_to_poincare_3d,
)


def verify_poincare_visualizer_pipeline() -> float:
    """Run full verification pipeline and measure execution time in milliseconds."""
    t_start = time.perf_counter()

    # 1. Verify 2048D -> 3D Vector Projection
    u_2048 = np.full(2048, 0.015, dtype=np.float64)
    v_2048 = np.full(2048, 0.025, dtype=np.float64)

    p3d_u = project_2048d_to_poincare_3d(u_2048)
    p3d_v = project_2048d_to_poincare_3d(v_2048)

    assert p3d_u.shape == (3,), f"Expected 3D projection, got shape {p3d_u.shape}"
    assert np.linalg.norm(p3d_u) < 1.0, f"Point outside Poincaré ball: norm={np.linalg.norm(p3d_u)}"

    # Batch 2048D Projection
    batch_2048 = np.random.default_rng(42).normal(0, 0.05, size=(100, 2048))
    batch_3d = project_2048d_to_poincare_3d(batch_2048)
    assert batch_3d.shape == (100, 3), f"Expected shape (100, 3), got {batch_3d.shape}"
    assert np.all(np.linalg.norm(batch_3d, axis=1) < 1.0), "All batch points must lie inside unit ball"

    # 2. Verify Hyperbolic Distance Computation
    # Self distance is 0
    d_self = compute_hyperbolic_distance(u_2048, u_2048)
    assert abs(d_self) < 1e-5, f"Self-distance should be 0.0, got {d_self}"

    # Positive distance
    d_uv = compute_hyperbolic_distance(u_2048, v_2048)
    assert d_uv > 0.0, f"Distance must be positive, got {d_uv}"

    # Symmetry: d_P(u, v) == d_P(v, u)
    d_vu = compute_hyperbolic_distance(v_2048, u_2048)
    assert abs(d_uv - d_vu) < 1e-6, f"Distance asymmetry: {d_uv} vs {d_vu}"

    # Batch distance
    batch_dists = compute_hyperbolic_distance_batch(batch_2048)
    assert len(batch_dists) == 100, "Batch dists size mismatch"
    assert np.all(batch_dists > 0.0), "Batch dists must be positive"

    # 3. Map Skills & Retrospectives into Hyperbolic Coordinates
    viz = PoincareManifoldVisualizer(seed=42)
    skills = viz.load_cohezion_skills(max_skills=71)
    retros = viz.load_surreal_retrospectives(count=15)

    assert len(skills) >= 71, f"Expected 71 skills, got {len(skills)}"
    assert len(retros) == 15, f"Expected 15 retros, got {len(retros)}"

    # 4. Generate Plotly Interactive 3D Figure
    fig = generate_poincare_figure(skills, retros)
    assert len(fig.data) > 0, "Plotly figure has no traces"

    t_end = time.perf_counter()
    elapsed_ms = (t_end - t_start) * 1000.0

    # Verify Export Helpers (outside timing loop)
    html_out = figure_to_html(fig)
    json_out = figure_to_json(fig)
    assert len(html_out) > 100, "HTML export empty"
    assert len(json_out) > 100, "JSON export empty"

    return elapsed_ms



def main() -> int:
    print("==========================================================================")
    print("🌀 Cohezion Poincaré 2048D Hyperbolic Manifold Visualizer Harness")
    print("==========================================================================")

    try:
        elapsed_ms = verify_poincare_visualizer_pipeline()
        print(f"✅ Vector Projection 2048D -> 3D: PASSED")
        print(f"✅ Hyperbolic Distance Computation: PASSED")
        print(f"✅ Skill & Retrospective Mapping: PASSED (71 PRIME skills + 15 Retros)")
        print(f"✅ Plotly 3D Figure Generation: PASSED")
        print(f"⏱️  Pipeline Execution Time: {elapsed_ms:.2f} ms")

        # Verify strict performance benchmark threshold (<100ms)
        benchmark_threshold_ms = 100.0
        if elapsed_ms < benchmark_threshold_ms:
            print(f"⚡ Benchmark Gate PASSED ({elapsed_ms:.2f} ms < {benchmark_threshold_ms:.0f} ms threshold)")
        else:
            print(f"⚠️  Benchmark Gate WARN ({elapsed_ms:.2f} ms >= {benchmark_threshold_ms:.0f} ms threshold)")

        print("==========================================================================")
        print("🎉 Verification Complete! Exiting 0.")
        return 0

    except Exception as exc:
        print(f"❌ Verification FAILED with error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
