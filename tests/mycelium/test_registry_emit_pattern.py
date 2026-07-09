"""Regression test for MyceliumRegistry._emit_pattern_event.

Captures the 2026-06-03 harness-bash-unification session finding that the
module's `cluster.size` is a `@property` (not a method) and the
`_emit_pattern_event` correctly uses it as a property. Earlier the retro
flagged a 'bug' that turned out to be in the test code, not the module —
this test guards against the module regressing in either direction.
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from cohezion.mycelium.registry import MyceliumCluster, MyceliumRegistry
from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind


def test_cluster_size_is_property_not_method():
    """`size` is a @property on the dataclass — accessing it as a method
    raises TypeError. The module code uses it as a property, which is
    correct. This test pins the API contract."""
    c = MyceliumCluster(
        cluster_id="mycelium-test",
        centroid_twelve_d={},
        centroid_fabric={},
    )
    # Property access: OK
    assert c.size == 0
    # Method call would raise — keep this commented to document the contract
    # try:
    #     c.size()
    # except TypeError:
    #     pass


def test_emit_pattern_event_does_not_raise():
    """`MyceliumRegistry._emit_pattern_event(cluster)` must not raise for a
    freshly-created cluster (cluster.size == 0). Guards against the
    historical concern that `cluster.size` (a property) was being called
    as a method."""
    registry = MyceliumRegistry()
    cluster = MyceliumCluster(
        cluster_id="mycelium-0",
        centroid_twelve_d={},
        centroid_fabric={},
    )
    registry.clusters.append(cluster)
    # Should not raise TypeError or any other exception
    registry._emit_pattern_event(cluster)


def test_emit_pattern_event_after_threshold_crossing():
    """When a cluster's size crosses `pattern_size_threshold`, the registry
    auto-emits the pattern event. We set threshold=1 so the very first
    event triggers emission, and verify the registry state is consistent
    afterward."""
    registry = MyceliumRegistry(pattern_size_threshold=1)
    event = PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id="u1",
        coherence=0.5,
        agent_id="agent-1",
    )
    registry._on_event(event)
    assert len(registry.clusters) == 1
    assert registry.clusters[0].size == 1
    # pattern_emitted should be True after crossing the threshold of 1
    assert registry.clusters[0].pattern_emitted is True
    # And calling _emit_pattern_event again should not raise
    registry._emit_pattern_event(registry.clusters[0])
