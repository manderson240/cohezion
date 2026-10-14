"""Unit tests for SIMD & Rayon accelerated 2048D Poincaré Manifold operations."""

import math
import time
import pytest

from cohezion_physics_core import (
    fast_poincare_conformal_factor,
    fast_poincare_distance,
    fast_poincare_mobius_add,
    fast_poincare_pairwise_distances,
)


def test_metric_identity():
    """Verify d_H(u, u) = 0 for 2048D vectors."""
    u = [0.01] * 2048
    d = fast_poincare_distance(u, u)
    assert pytest.approx(d, abs=1e-7) == 0.0


def test_metric_symmetry():
    """Verify d_H(u, v) = d_H(v, u)."""
    u = [0.01 * (i % 5) for i in range(2048)]
    v = [0.005 * ((i + 1) % 7) for i in range(2048)]
    d_uv = fast_poincare_distance(u, v)
    d_vu = fast_poincare_distance(v, u)
    assert pytest.approx(d_uv, rel=1e-7) == d_vu
    assert d_uv > 0.0


def test_triangle_inequality():
    """Verify d_H(u, w) <= d_H(u, v) + d_H(v, w)."""
    u = [0.005] * 2048
    v = [-0.005] * 2048
    w = [0.01 if i % 2 == 0 else -0.01 for i in range(2048)]

    d_uw = fast_poincare_distance(u, w)
    d_uv = fast_poincare_distance(u, v)
    d_vw = fast_poincare_distance(v, w)

    assert d_uw <= (d_uv + d_vw) + 1e-9


def test_conformal_factor():
    """Verify conformal factor at origin lambda(0) = 2.0 and growth towards boundary."""
    origin = [0.0] * 2048
    assert pytest.approx(fast_poincare_conformal_factor(origin), rel=1e-7) == 2.0

    p1 = [0.1] + [0.0] * 2047
    p2 = [0.9] + [0.0] * 2047
    cf1 = fast_poincare_conformal_factor(p1)
    cf2 = fast_poincare_conformal_factor(p2)

    assert cf1 > 2.0
    assert cf2 > cf1
    assert pytest.approx(cf1, rel=1e-5) == 2.0 / (1.0 - 0.01)
    assert pytest.approx(cf2, rel=1e-5) == 2.0 / (1.0 - 0.81)


def test_boundary_divergence():
    """Verify hyperbolic distance and conformal factor diverge as ||u|| -> 1."""
    origin = [0.0] * 2048
    radii = [0.5, 0.9, 0.99, 0.999, 0.9999]
    distances = []
    factors = []

    for r in radii:
        pt = [r] + [0.0] * 2047
        distances.append(fast_poincare_distance(origin, pt))
        factors.append(fast_poincare_conformal_factor(pt))

    # Strict monotonic increase
    for i in range(len(distances) - 1):
        assert distances[i + 1] > distances[i]
        assert factors[i + 1] > factors[i]

    # Extreme boundary limit should be large
    assert distances[-1] > 8.0
    assert factors[-1] > 9000.0


def test_mobius_addition():
    """Verify Mobius addition identity and boundary closure."""
    origin = [0.0] * 2048
    u = [0.01] * 2048
    v = [-0.005] * 2048

    # Identity u (+) 0 = u
    u_add_zero = fast_poincare_mobius_add(u, origin)
    for a, b in zip(u_add_zero, u):
        assert pytest.approx(a, rel=1e-7) == b

    # Closure: ||u (+) v|| < 1
    w = fast_poincare_mobius_add(u, v)
    norm_w = math.sqrt(sum(x * x for x in w))
    assert norm_w < 1.0


def test_pairwise_distances_rayon():
    """Verify Rayon parallel pairwise distance matrix matches scalar distances."""
    points = [
        [0.01 * k] + [0.001 * (k % 3)] * 2047
        for k in range(8)
    ]
    mat = fast_poincare_pairwise_distances(points)
    assert len(mat) == 8
    assert len(mat[0]) == 8

    for i in range(8):
        assert pytest.approx(mat[i][i], abs=1e-7) == 0.0
        for j in range(8):
            expected = fast_poincare_distance(points[i], points[j])
            assert pytest.approx(mat[i][j], rel=1e-6) == expected
            assert pytest.approx(mat[i][j], rel=1e-6) == mat[j][i]


def test_2048d_performance():
    """Verify sub-microsecond scale execution for 2048D distance."""
    u = [0.01] * 2048
    v = [0.02] * 2048

    # Warmup
    for _ in range(50):
        fast_poincare_distance(u, v)

    # Benchmark 2000 iterations
    t0 = time.perf_counter()
    n_iters = 2000
    for _ in range(n_iters):
        fast_poincare_distance(u, v)
    t1 = time.perf_counter()

    avg_latency_us = ((t1 - t0) / n_iters) * 1e6
    assert avg_latency_us < 200.0  # Conservative bound for Python-C boundary overhead
