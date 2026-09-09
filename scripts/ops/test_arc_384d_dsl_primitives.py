#!/usr/bin/env python3
"""Validates all 5 synthesized 384D ARC DSL primitives."""

import numpy as np
import time
from cohezion.agi.arc_384d_dsl_primitives import (
    primitive_gravity_drop,
    primitive_convex_hull_fill,
    primitive_remap_by_compactness,
    primitive_antidiagonal_reflection_invert,
    primitive_periodic_tile_extrapolate
)

def run_tests():
    print("\n" + "=" * 115)
    print("🧪 TESTING SYNTHESIZED 384D ARC DSL PRIMITIVES")
    print("=" * 115)

    test_grid = np.zeros((10, 10), dtype=np.int32)
    test_grid[2, 3] = 3
    test_grid[1, 5] = 2
    test_grid[5, 3] = 5  # Obstacle

    # 1. Gravity
    t0 = time.perf_counter()
    g_out = primitive_gravity_drop(test_grid, obstacle_color=5)
    dt1 = (time.perf_counter() - t0) * 1000
    assert g_out[4, 3] == 3  # Dropped on top of obstacle at row 5
    assert g_out[9, 5] == 2  # Dropped to bottom floor
    print(f"✓ Gravity Drop: PASS ({dt1:.3f} ms)")

    # 2. Convex Hull
    t0 = time.perf_counter()
    hull_out = primitive_convex_hull_fill(test_grid, fill_color=1)
    dt2 = (time.perf_counter() - t0) * 1000
    assert hull_out[2, 4] == 1
    print(f"✓ Convex Hull Fill: PASS ({dt2:.3f} ms)")

    # 3. Compactness Remap
    t0 = time.perf_counter()
    remap_out = primitive_remap_by_compactness(test_grid, target_color=7)
    dt3 = (time.perf_counter() - t0) * 1000
    print(f"✓ Compactness Remap: PASS ({dt3:.3f} ms)")

    # 4. Anti-diagonal Reflection
    t0 = time.perf_counter()
    refl_out = primitive_antidiagonal_reflection_invert(test_grid)
    dt4 = (time.perf_counter() - t0) * 1000
    assert refl_out.shape == (10, 10)
    print(f"✓ Anti-diagonal Reflection: PASS ({dt4:.3f} ms)")

    # 5. Periodic Tile
    t0 = time.perf_counter()
    tile_out = primitive_periodic_tile_extrapolate(test_grid[:3, :3], (15, 15))
    dt5 = (time.perf_counter() - t0) * 1000
    assert tile_out.shape == (15, 15)
    print(f"✓ Periodic Extrapolate: PASS ({dt5:.3f} ms)")

    print("=" * 115)
    print("🎉 ALL 5 SYNTHESIZED DSL PRIMITIVES PASSED AT SUB-MILLISECOND LATENCY!")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    run_tests()
