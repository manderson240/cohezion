from cohezion.cache.semantic_cache_system import CacheHit, SemanticCacheSystem
from cohezion.inference.batch_optimizer import BatchExecutionResult, BatchOptimizer
from cohezion.physics.poincare_manifold import PoincareManifoldND


def test_batch_optimizer():
    optimizer = BatchOptimizer(max_batch_size=4)
    optimizer.enqueue_request("req1", "Explain Poincaré geodesics.", target_hardware="NPU")
    optimizer.enqueue_request("req2", "Explain Christoffel symbols.", target_hardware="NPU")

    res = optimizer.flush_batch(target_hardware="NPU")
    assert isinstance(res, BatchExecutionResult)
    assert res.batch_size == 2
    assert res.hardware_lane == "NPU"
    assert 0.0 <= res.padding_efficiency <= 1.0


def test_semantic_cache_system_l1_and_l2():
    cache = SemanticCacheSystem(l1_capacity=10, l2_distance_threshold=0.25)
    p1 = PoincareManifoldND.project([0.01] * 256, target_dim=256)
    p2 = PoincareManifoldND.project([0.015] * 256, target_dim=256)

    cache.put("Test prompt 1", "Cached Answer 1", state_vector=p1)

    # Test L1 Hit
    l1_hit = cache.get("Test prompt 1")
    assert isinstance(l1_hit, CacheHit)
    assert l1_hit.tier == "L1_LRU"
    assert l1_hit.value == "Cached Answer 1"

    # Test L2 Hyperbolic Distance Hit
    l2_hit = cache.get("Different prompt", state_vector=p2)
    assert isinstance(l2_hit, CacheHit)
    assert l2_hit.tier == "L2_Hyperbolic"
    assert l2_hit.value == "Cached Answer 1"
