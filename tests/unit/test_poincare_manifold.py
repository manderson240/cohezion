import math

import pytest

from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND


def test_poincare_point_validation():
    # Valid 12D point inside unit ball
    coords_12d = tuple([0.1] * 12)
    pt12 = PoincarePoint(coords_12d)
    assert pt12.dim == 12
    assert pt12.norm < 1.0

    # Valid higher-dimensional points (26D, 256D, 2048D)
    for dim in (16, 26, 32, 256, 2048):
        c = tuple([0.01] * dim)
        pt = PoincarePoint(c)
        assert pt.dim == dim
        assert pt.norm < 1.0

    # Point outside unit ball raises ValueError
    with pytest.raises(ValueError, match="inside the unit ball"):
        PoincarePoint(tuple([0.5] * 12))  # norm^2 = 12 * 0.25 = 3.0 >= 1.0


def test_poincare_project():
    large_coords = tuple([0.8] * 12)  # Outside unit ball
    pt = PoincareManifoldND.project(large_coords)
    assert len(pt.coords) == 12
    assert pt.norm < 1.0
    assert pt.norm <= PoincareManifoldND.MAX_RADIUS

    # Project 256D point
    large_256 = tuple([0.5] * 256)
    pt256 = PoincareManifoldND.project(large_256)
    assert pt256.dim == 256
    assert pt256.norm <= PoincareManifoldND.MAX_RADIUS


def test_poincare_distance():
    p1 = PoincareManifoldND.project(tuple([0.1] * 12))
    p2 = PoincareManifoldND.project(tuple([0.2] * 12))

    dist = PoincareManifoldND.distance(p1, p2)
    assert dist > 0.0
    assert math.isfinite(dist)

    # Self distance is 0
    assert pytest.approx(PoincareManifoldND.distance(p1, p1), abs=1e-5) == 0.0


def test_curvature_regularization_loss():
    pts = [PoincareManifoldND.project(tuple([0.05 * i] * 12)) for i in range(4)]
    loss = PoincareManifoldND.curvature_regularization_loss(pts)
    assert loss > 0.0
    assert math.isfinite(loss)
