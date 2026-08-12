import math
import pytest
import numpy as np
from cohezion.flume.j_space_latent_manifold import JSpaceLatentManifold, JSpacePoint


def test_j_space_inner_product_and_classification():
    manifold = JSpaceLatentManifold(timelike_dim=3, spacelike_dim=9)

    v_time = [2.0, 1.0, 1.0] + [0.1] * 9
    v_space = [0.1, 0.1, 0.1] + [2.0] * 9
    v_lightcone = [1.0, 1.0, 1.0] + [1.0, 1.0, 1.0] + [0.0] * 6

    pt_t = manifold.classify_point(v_time)
    pt_s = manifold.classify_point(v_space)
    pt_l = manifold.classify_point(v_lightcone)

    assert pt_t.classification == "TIMELIKE"
    assert pt_s.classification == "SPACELIKE"
    assert pt_l.classification == "LIGHTCONE_HIHO"


def test_j_unitary_boost_isometry():
    manifold = JSpaceLatentManifold(timelike_dim=3, spacelike_dim=9)
    v = [1.5, 0.5, 0.5] + [0.2] * 9

    v_boosted = manifold.apply_j_boost(v, boost_parameter=1.2)
    norm_orig = manifold.j_norm_squared(v)
    norm_boosted = manifold.j_norm_squared(v_boosted)

    assert math.isclose(norm_orig, norm_boosted, abs_tol=1e-8)


def test_j_geodesic_distance():
    manifold = JSpaceLatentManifold(timelike_dim=3, spacelike_dim=9)
    u = [1.0] * 12
    v = [2.0] * 12

    dist = manifold.compute_j_geodesic_distance(u, v)
    assert dist >= 0.0
