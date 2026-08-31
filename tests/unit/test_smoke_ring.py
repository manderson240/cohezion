from cohezion.physics.poincare_manifold import PoincareManifoldND
from cohezion.physics.smoke_ring_manifold import SmokeRingAttractor, SmokeRingManifold


def test_smoke_ring_manifold_projection():
    ring_engine = SmokeRingManifold(major_radius=0.50, minor_radius=0.10)
    p2048 = PoincareManifoldND.project([0.01] * 2048, target_dim=2048)

    ring = ring_engine.project_to_smoke_ring(p2048)
    assert isinstance(ring, SmokeRingAttractor)
    assert len(ring.toroidal_point) == 3
    assert ring.major_radius == 0.50
    assert ring.minor_radius == 0.10
    assert 0.0 <= ring.penetration_depth <= 1.0
    assert 0.0 <= ring.ring_coherence <= 1.0
