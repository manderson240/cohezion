"""Unit tests for Cohezion Spatiotemporal Swarm State Tracking."""

import numpy as np
import pytest

from cohezion.tracking import (
    Detection,
    EuclideanAssociationPolicy,
    SwarmState,
    TrackingByDetectionEngine,
)


def test_swarm_tracking_association_and_state():
    """Verify track birth, linear motion association, and swarm state metrics."""
    tracker = TrackingByDetectionEngine(max_distance=5.0, max_misses=2)

    # Frame 0: Two agents born at (0, 0) and (10, 10)
    det0 = [
        Detection(timestamp=0.0, position=np.array([0.0, 0.0]), entity_type="agent_a"),
        Detection(timestamp=0.0, position=np.array([10.0, 10.0]), entity_type="agent_b"),
    ]
    s0 = tracker.step(det0, timestamp=0.0)
    assert len(s0.active_tracks) == 2
    assert np.allclose(s0.center_of_mass, np.array([5.0, 5.0]))

    # Frame 1: Agents move to (1, 1) and (11, 11)
    det1 = [
        Detection(timestamp=1.0, position=np.array([1.0, 1.0]), entity_type="agent_a"),
        Detection(timestamp=1.0, position=np.array([11.0, 11.0]), entity_type="agent_b"),
    ]
    s1 = tracker.step(det1, timestamp=1.0)
    assert len(s1.active_tracks) == 2
    for trk in s1.active_tracks:
        assert trk.age == 2
        assert trk.total_hits == 2
        # Velocity should be ~ (1, 1)
        assert np.allclose(trk.velocity, np.array([1.0, 1.0]))

    assert s1.velocity_flux > 0.0


def test_swarm_mitosis_com_conservation():
    """Verify lineage branching/mitosis detection via Center-of-Mass conservation."""
    tracker = TrackingByDetectionEngine(
        max_distance=1.5,
        max_misses=0,  # Immediately becomes candidate parent on miss
        min_hits=1,
        mitosis_epsilon=1.0,
        mitosis_daughter_separation=2.0,
    )

    # Frame 0: Parent at (10.0, 10.0)
    parent_pos = np.array([10.0, 10.0])
    s0 = tracker.step([Detection(timestamp=0.0, position=parent_pos)], timestamp=0.0)
    assert len(s0.active_tracks) == 1
    parent_id = s0.active_tracks[0].track_id

    # Frame 1: Parent divides into two daughters at (8.0, 10.0) and (12.0, 10.0)
    # Center of mass = (8 + 12)/2 = 10.0, distance between daughters = 4.0 >= 2.0
    d1 = Detection(timestamp=1.0, position=np.array([8.0, 10.0]), intensity_or_mass=1.0)
    d2 = Detection(timestamp=1.0, position=np.array([12.0, 10.0]), intensity_or_mass=1.0)

    s1 = tracker.step([d1, d2], timestamp=1.0)

    assert len(s1.lineage_events) == 1
    event = s1.lineage_events[0]
    assert event["event_type"] == "mitosis"
    assert event["parent_track_id"] == parent_id
    assert len(event["children_track_ids"]) == 2

    # Verify daughter tracks exist and reference parent
    for cid in event["children_track_ids"]:
        assert cid in tracker.tracks
        assert tracker.tracks[cid].parent_track_id == parent_id
