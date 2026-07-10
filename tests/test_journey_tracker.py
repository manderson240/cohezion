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


# ---------------------------------------------------------------------------
# #138: Cross-session identity persistence (GIC Identity dimension)
# ---------------------------------------------------------------------------


class TestCrossSessionIdentity:
    """V-model tests for JourneyTracker cross-session identity (#138).

    GIC Identity dimension: the agent maintains a stable self-concept
    (agent_id, session_count, lifetime_op_counts) across process restarts
    via JSON persistence in ~/.cohezion/journey_identity.json.
    """

    # T1 structural: required attributes must exist on JourneyTracker

    def test_agent_id_attribute_exists(self):
        jt = JourneyTracker()
        assert hasattr(jt, "agent_id"), "JourneyTracker must have agent_id property"

    def test_save_identity_method_exists(self):
        jt = JourneyTracker()
        assert callable(getattr(jt, "save_identity", None))

    def test_restore_identity_method_exists(self):
        jt = JourneyTracker()
        assert callable(getattr(jt, "restore_identity", None))

    def test_lifetime_op_counts_attribute_exists(self):
        jt = JourneyTracker()
        assert hasattr(jt, "_lifetime_op_counts")
        assert isinstance(jt._lifetime_op_counts, dict)

    # T2 discriminating: agent_id persists across instances via save/restore

    def test_agent_id_is_stable_string(self):
        jt = JourneyTracker()
        aid = jt.agent_id
        assert isinstance(aid, str) and len(aid) > 0

    def test_save_restore_preserves_agent_id(self, tmp_path):
        """A new JourneyTracker restored from a save has the SAME agent_id.

        Wrong impl: generates a new UUID on every __init__ (never restores).
        Discriminating: the two ids must match, not merely be non-empty.
        """
        identity_file = tmp_path / "journey_identity.json"
        jt1 = JourneyTracker()
        original_id = jt1.agent_id
        jt1.save_identity(path=identity_file)

        jt2 = JourneyTracker()
        restored = jt2.restore_identity(path=identity_file)
        assert restored is True, "restore_identity() should return True on success"
        assert jt2.agent_id == original_id, (
            f"Restored agent_id {jt2.agent_id!r} != original {original_id!r}"
        )

    def test_session_count_increments_across_saves(self, tmp_path):
        """session_count increases each time save_identity() is called.

        Wrong impl: always writes 0.  Discriminating: count must strictly
        increase across two saves.
        """
        identity_file = tmp_path / "journey_identity.json"
        jt1 = JourneyTracker()
        jt1.save_identity(path=identity_file)

        jt2 = JourneyTracker()
        jt2.restore_identity(path=identity_file)
        count_after_first = jt2._session_count
        jt2.save_identity(path=identity_file)

        jt3 = JourneyTracker()
        jt3.restore_identity(path=identity_file)
        assert jt3._session_count > count_after_first, (
            "session_count must increase after a second save"
        )

    def test_restore_returns_false_when_no_file(self, tmp_path):
        """restore_identity() returns False when the identity file doesn't exist."""
        jt = JourneyTracker()
        result = jt.restore_identity(path=tmp_path / "nonexistent.json")
        assert result is False

    def test_save_identity_returns_dict_with_required_keys(self, tmp_path):
        """save_identity() must return the serialized dict with required fields."""
        identity_file = tmp_path / "journey_identity.json"
        jt = JourneyTracker()
        saved = jt.save_identity(path=identity_file)
        assert isinstance(saved, dict)
        for key in ("agent_id", "session_count", "lifetime_op_counts"):
            assert key in saved, f"save_identity() result missing key: {key!r}"

    def test_agent_id_is_injected_via_constructor(self):
        """JourneyTracker(agent_id=X) preserves X as the identity.

        Enables test isolation and cross-agent identity hand-off.
        """
        jt = JourneyTracker(agent_id="test-agent-42")
        assert jt.agent_id == "test-agent-42"


# ---------------------------------------------------------------------------
# JI1: TrajectoryPoint.action field (harness invariant JI1)
# ---------------------------------------------------------------------------


class TestTrajectoryPointAction:
    """JI1: TrajectoryPoint.action captures tier_used from CB16 metrics by default."""

    def _make_result(self, tier: str = "npu", **extra_metrics) -> "ExecutionResult":
        return ExecutionResult(
            success=True,
            output="ok",
            metrics={"tier_used": tier, **extra_metrics},
            duration_seconds=0.1,
            token_metrics={},
        )

    def test_t1_action_field_exists_with_str_default(self) -> None:
        """T1 structural: TrajectoryPoint has action field defaulting to empty string."""
        import dataclasses

        fields = {f.name: f for f in dataclasses.fields(TrajectoryPoint)}
        assert "action" in fields, "TrajectoryPoint missing 'action' field (JI1)"
        assert fields["action"].default == "", "'action' default must be empty string"

    def test_t1_track_execution_accepts_action_kwarg(self) -> None:
        """T1 structural: track_execution signature includes optional action kwarg."""
        import inspect

        sig = inspect.signature(JourneyTracker.track_execution)
        assert "action" in sig.parameters, "track_execution missing 'action' parameter"
        assert sig.parameters["action"].default == ""

    def test_t2_action_captured_from_tier_used(self) -> None:
        """T2 discriminating: action defaults to tier_used when not explicitly provided.

        Wrong impl (action stays empty) would leave point.action == '' → fails.
        """
        tracker = JourneyTracker()
        result = self._make_result(tier="npu")
        point = tracker.track_execution(result, "classify task", "classify")
        assert point.action == "npu", f"Expected action='npu' from tier_used, got {point.action!r}"

    def test_t2_explicit_action_overrides_tier_used(self) -> None:
        """T2 discriminating: explicit action arg takes priority over tier_used.

        Wrong impl (always uses tier_used) would return 'cpu' instead of explicit value.
        """
        tracker = JourneyTracker()
        result = self._make_result(tier="cpu")
        point = tracker.track_execution(result, "escalated task", "reason", action="igpu:escalated")
        assert point.action == "igpu:escalated", (
            f"Explicit action must override tier_used, got {point.action!r}"
        )

    def test_action_empty_when_no_tier_and_no_explicit(self) -> None:
        """When tier_used absent and no explicit action, action stays empty string."""
        tracker = JourneyTracker()
        result = ExecutionResult(
            success=True,
            output="ok",
            metrics={},  # no tier_used
            duration_seconds=0.1,
            token_metrics={},
        )
        point = tracker.track_execution(result, "simple task", "classify")
        assert point.action == "", f"Expected empty action, got {point.action!r}"
