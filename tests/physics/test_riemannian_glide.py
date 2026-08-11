"""Tests for RiemannianGlideTrajectory geodesic integration (#95)."""

import math

from cohezion.physics import RiemannianGlideTrajectory


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def test_step_changes_position():
    t = RiemannianGlideTrajectory(_identity(2), [0.0, 0.0], [1.0, 2.0])
    p = t.step(0.1)
    assert p == [0.1, 0.2]
    assert t.position == [0.1, 0.2]


def test_arc_length_positive():
    t = RiemannianGlideTrajectory(_identity(2), [0.0, 0.0], [1.0, 0.0])
    assert t.arc_length(n_steps=10, dt=0.01) > 0.0


def test_curvature_proxy_identity():
    t = RiemannianGlideTrajectory(_identity(3), [0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    assert t.curvature_proxy() == 1.0


def test_arc_length_element_euclidean():
    # 3-4-5 right triangle: |(3,4)| = 5 under the identity metric.
    t = RiemannianGlideTrajectory(_identity(2), [0.0, 0.0], [3.0, 4.0])
    assert math.isclose(t.arc_length_element(), 5.0)
