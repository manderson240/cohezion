import math
import pytest
from cohezion.contracts import PoincarePoint
from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.flatland_projection import FlatlandProjector, FlatlandSlice

def test_flatland_slice_hypersphere():
    pt = PoincareManifoldND.project(tuple([0.1] * 12))
    # At w=0, slice radius equals hyper-sphere radius
    r_full = pt.norm
    r_slice_0 = FlatlandProjector.slice_hypersphere(pt, r_full, w_depth=0.0)
    assert pytest.approx(r_slice_0, abs=1e-5) == r_full

    # At w > r_full, slice radius is 0 (outside Flatland plane)
    r_slice_out = FlatlandProjector.slice_hypersphere(pt, r_full, w_depth=r_full + 0.1)
    assert r_slice_out == 0.0

def test_flatland_project_to_flatland():
    for dim in (12, 16, 26, 32, 256, 2048):
        raw_coords = tuple([0.02 * (i + 1) for i in range(dim)])
        pt = PoincareManifoldND.project(raw_coords)
        slice_res = FlatlandProjector.project_to_flatland(pt)

        assert isinstance(slice_res, FlatlandSlice)
        assert slice_res.original_dim == dim
        assert math.isfinite(slice_res.slice_radius)
        assert slice_res.conformal_factor >= 2.0
