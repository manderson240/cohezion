import threading
import time
import pytest
from cohezion.mycelium.registry import MyceliumRegistry, MyceliumCluster
from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind

def test_registry_singleton_flow():
    """Verify get_instance() returns the same instance and reset_instance() clears it."""
    # Reset first to ensure clean state
    MyceliumRegistry.reset_instance()
    
    r1 = MyceliumRegistry.get_instance()
    r2 = MyceliumRegistry.get_instance()
    
    assert r1 is r2
    assert isinstance(r1, MyceliumRegistry)
    
    MyceliumRegistry.reset_instance()
    r3 = MyceliumRegistry.get_instance()
    assert r3 is not r1

def test_registry_singleton_thread_safety():
    """Verify concurrent thread access to get_instance() is thread-safe and returns one instance."""
    MyceliumRegistry.reset_instance()
    instances = []
    
    def worker():
        inst = MyceliumRegistry.get_instance()
        instances.append(inst)
        
    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert len(instances) == 20
    first = instances[0]
    for inst in instances:
        assert inst is first

def test_registry_cluster_limits_and_fifo_eviction():
    """Verify that when clusters exceed 500, the oldest inactive cluster is evicted."""
    MyceliumRegistry.reset_instance()
    registry = MyceliumRegistry.get_instance()
    registry.radius = 0.01  # very small radius to force new clusters
    
    # Generate 501 different events to force 501 clusters
    for i in range(501):
        event = PrecipitationEvent(
            kind=PrecipitationKind.WITNESS_MARK,
            universe_id=f"univ_{i}",
            coherence=0.8,
            twelve_d={
                "x": 0.5, "y": 0.5, "z": 0.5, "time": 0.5, "physics": 0.5,
                "biology": 0.5, "logic": 0.5, "quantum": 0.5, "field": 0.5,
                "control": 0.5, "novelty": 0.5, "precipitation": 0.5
            },
            fabric_breakdown={"Space": 0.5, "Field": 0.5, "Control": 0.5, "Precipitation": 0.5},
            payload={"model_id": f"model_{i}", "task": "code", "index": i}
        )
        # Shift coordinate significantly to force different cluster
        event.twelve_d["x"] = 10.0 * i
        event.fabric_breakdown["Space"] = 10.0 * i
        registry._on_event(event)
        
    # Total clusters should be capped at 500
    assert len(registry.clusters) == 500
    # The first cluster (index 0, centroid x=0.0) should have been evicted (FIFO)
    cluster_ids = {c.cluster_id for c in registry.clusters}
    assert "mycelium-0" not in cluster_ids
    assert "mycelium-500" in cluster_ids

def test_query_patterns():
    """Verify query_patterns returns correct details when filtering by family and task."""
    MyceliumRegistry.reset_instance()
    registry = MyceliumRegistry.get_instance()
    
    # We manually create a cluster and members to test query_patterns filtering
    cluster = MyceliumCluster(
        cluster_id="mycelium-test-0",
        centroid_twelve_d={},
        centroid_fabric={},
        member_event_ids=["evt-1"],
        member_agent_ids=set(),
        member_universe_ids={"univ-1"}
    )
    cluster.member_families = {"qwen3"}
    cluster.member_tasks = {"code"}
    cluster.mean_coherence = 0.95
    
    registry.clusters.append(cluster)
    
    # Query for matching family + task
    results = registry.query_patterns("qwen3", "code")
    assert len(results) == 1
    assert results[0]["cluster_id"] == "mycelium-test-0"
    assert results[0]["size"] == 1
    assert results[0]["mean_coherence"] == 0.95
    
    # Query for mismatch
    assert len(registry.query_patterns("llama3", "code")) == 0
    assert len(registry.query_patterns("qwen3", "generate")) == 0
