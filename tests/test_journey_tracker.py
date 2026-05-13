"""Smoke tests for JourneyTracker, JourneyPersistence,
and CompoundMetricsCollector.

Replaces stash-era tests (Sessions 25-29) with HEAD-compatible
track_execution() API and persistence round-trip tests.
"""

from __future__ import annotations

import pytest

from cohezion.compound.executor import ExecutionResult
from cohezion.compound.journey_tracker import JourneyTracker, TrajectoryPoint


# ---------------------------------------------------------------------------
# JourneyTracker smoke tests
# ---------------------------------------------------------------------------


class TestJourneyTrackerSmoke:
    """Verify HEAD's JourneyTracker.track_execution() API."""

    def test_track_execution_returns_trajectory_point(self) -> None:
        tracker = JourneyTracker()
        result = ExecutionResult(
            success=True,
            output="test output",
            metrics={"coherence": 0.7},
            duration_seconds=1.5,
            token_metrics={"cache_hit_rate": 0.6},
        )
        point = tracker.track_execution(result, "Generate ideas", "generate")
        assert isinstance(point, TrajectoryPoint)
        assert point.coherence == 0.7
        assert point.efficiency == 0.6
        assert point.operation_type == "generate"
        assert len(point.dimensions) == 12

    def test_track_execution_defaults(self) -> None:
        tracker = JourneyTracker()
        result = ExecutionResult(
            success=False,
            output="error",
            metrics={},
            duration_seconds=0.5,
        )
        point = tracker.track_execution(result, "Analyze data", "analyze")
        assert point.coherence == 0.5  # default
        assert point.efficiency == 0.5  # default (no token_metrics)

    def test_compute_trajectory_quality(self) -> None:
        tracker = JourneyTracker()
        points = []
        for op in ["generate", "analyze", "search"]:
            result = ExecutionResult(
                success=True,
                output=f"output for {op}",
                metrics={"coherence": 0.6},
                duration_seconds=1.0,
            )
            points.append(tracker.track_execution(result, f"Task {op}", op))

        quality = tracker.compute_trajectory_quality(points)
        assert "mean_phi_score" in quality
        assert "mean_coherence" in quality
        assert "smoothness" in quality
        assert quality["mean_coherence"] == pytest.approx(0.6, abs=0.01)

    def test_compute_trajectory_quality_empty(self) -> None:
        tracker = JourneyTracker()
        quality = tracker.compute_trajectory_quality([])
        assert quality["mean_phi_score"] == 0.0


# ---------------------------------------------------------------------------
# JourneyPersistence smoke tests
# ---------------------------------------------------------------------------
# NOTE: Removed test_save_load_roundtrip and test_save_trajectory_point
# (Wave 3E). They referenced the old save_journey/load_journeys/
# save_trajectory_point API which was replaced by persist_batch/parquet.
# Coverage of the new API lives in tests/compound/test_exp_persistence/.


# ---------------------------------------------------------------------------
# CompoundMetricsCollector smoke tests
# ---------------------------------------------------------------------------


class TestCompoundMetricsCollectorSmoke:
    """Verify to_snapshot()/load_from_snapshot() round-trip."""

    def test_snapshot_roundtrip(self) -> None:
        from cohezion.compound.metrics import CompoundMetricsCollector

        c = CompoundMetricsCollector()
        c.record_execution("skill_a", True, 100, 50.0, "phi3")
        c.record_refinement("skill_a", "1.0", "1.1", 2)
        c.record_cycle("skill_a", 1, 1, 0.05, 100, 50.0)

        snap = c.to_snapshot()
        assert len(snap["executions"]) == 1
        assert len(snap["refinements"]) == 1
        assert len(snap["cycles"]) == 1

        c2 = CompoundMetricsCollector()
        c2.load_from_snapshot(snap)
        assert c2.total_executions == 1
        assert c2.total_refinements == 1
        assert c2.total_cycles == 1

    def test_empty_snapshot(self) -> None:
        from cohezion.compound.metrics import CompoundMetricsCollector

        c = CompoundMetricsCollector()
        snap = c.to_snapshot()
        assert snap["executions"] == []
        assert snap["refinements"] == []
        assert snap["cycles"] == []
