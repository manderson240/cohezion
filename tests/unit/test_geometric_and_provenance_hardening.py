"""Unit tests for Geometric Correspondence and Data Provenance Key Rotation."""

import math

from cohezion.flume.geometric_correspondence import GeometricCorrespondenceEngine
from cohezion.security.data_provenance_signer import DataProvenanceSigner


def test_poincare_distance_and_gradient_clipping():
    engine = GeometricCorrespondenceEngine()

    # 1. Test distance calculation
    u = (0.1, 0.2, 0.3)
    v = (0.4, 0.5, 0.1)
    dist = engine.compute_poincare_distance(u, v)
    assert dist > 0.0
    assert not math.isnan(dist)
    assert not math.isinf(dist)

    # 2. Test boundary clamping stability (||u|| >= 1.0)
    overflow_u = (1.5, 1.5, 1.5)
    overflow_v = (0.0, 0.0, 0.0)
    boundary_dist = engine.compute_poincare_distance(overflow_u, overflow_v)
    assert not math.isnan(boundary_dist)
    assert boundary_dist > 0.0

    # 3. Test Riemannian gradient computation & clipping
    grad = engine.compute_poincare_gradient(overflow_u, overflow_v, max_norm=5.0)
    assert len(grad) == 3
    grad_norm = math.sqrt(sum(g * g for g in grad))
    assert grad_norm <= 5.0001


def test_data_provenance_hmac_key_rotation():
    sample = {"instruction": "Train autonomous agent", "steps": 100}

    # Sign with default rotated v2 key
    sig_v2 = DataProvenanceSigner.sign_sample(sample, key_id="v2")
    assert sig_v2.startswith("v2:")
    assert DataProvenanceSigner.verify_sample(sample, sig_v2) is True

    # Sign with legacy v1 key and verify backwards compatibility
    sig_v1 = DataProvenanceSigner.sign_sample(sample, key_id="v1")
    assert sig_v1.startswith("v1:")
    assert DataProvenanceSigner.verify_sample(sample, sig_v1) is True

    # Tampered payload fails verification
    tampered_sample = {"instruction": "Train autonomous agent", "steps": 999}
    assert DataProvenanceSigner.verify_sample(tampered_sample, sig_v2) is False
