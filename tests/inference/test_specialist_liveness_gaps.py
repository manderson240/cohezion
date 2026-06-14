"""Item 77: specialist liveness gaps (report-only, TDD red→green).

`specialist_liveness_gaps(*, registry, check_fleet_fn)` partitions the 6
specialist Tasks into ``ready`` (lane UP → a verification attempt is possible)
and ``lane_down`` (lane DOWN / gap → can't be tested right now).

Each test fails a plausible wrong impl:
  - treats a DOWN lane as ready                  → test_down_lane_puts_specialist_in_lane_down
  - ignores gap rows (model_id=None)             → test_gap_specialist_always_in_lane_down
  - doesn't cover all six tasks                  → test_partitions_cover_all_six_specialists
  - overlaps ready ∩ lane_down                   → test_partitions_are_disjoint
  - calls the live probe instead of the injected fn → (fails at test collection time if live)
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

from cohezion.inference.registry import FleetRegistry, Task, get_registry
from cohezion.inference.specialist_coverage import (
    SPECIALIST_TASKS,
    SpecialistLivenessReport,
    specialist_liveness_gaps,
)


# ---------------------------------------------------------------------------
# Test helpers — no live I/O, no MagicMock
# ---------------------------------------------------------------------------


def _health_fn(up_lanes: frozenset[str]):
    """Build a deterministic check_fleet_fn that marks specific lanes as UP."""
    all_lanes = ["npu", "igpu_rocwmma", "igpu_unified", "cpu"]

    def _check():
        lanes_dict = {}
        for ln in all_lanes:
            status = SimpleNamespace(value="up" if ln in up_lanes else "down")
            lanes_dict[ln] = SimpleNamespace(status=status)
        return SimpleNamespace(lanes=lanes_dict)

    return _check


def _isolated_registry() -> FleetRegistry:
    """Deep-copied registry so modifications don't pollute the module singleton."""
    return FleetRegistry(models=copy.deepcopy(get_registry().models))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSpecialistLivenessGapsReturn:
    """Return type and structural invariants."""

    def test_returns_specialist_liveness_report(self) -> None:
        reg = _isolated_registry()
        fn = _health_fn(frozenset())
        result = specialist_liveness_gaps(registry=reg, check_fleet_fn=fn)
        assert isinstance(result, SpecialistLivenessReport)

    def test_ready_plus_lane_down_equals_six(self) -> None:
        """All 6 specialists must appear in exactly one partition."""
        reg = _isolated_registry()
        fn = _health_fn(frozenset())
        result = specialist_liveness_gaps(registry=reg, check_fleet_fn=fn)
        total = len(result.ready) + len(result.lane_down)
        assert total == len(SPECIALIST_TASKS), (
            f"expected {len(SPECIALIST_TASKS)} tasks total, got {total}"
        )


class TestPartitionCorrectness:
    """Core discriminating tests: partition logic must be right, not just fire."""

    def test_up_lane_puts_registered_specialist_in_ready(self) -> None:
        """When the specialist's lane is UP, the task row belongs in ready."""
        reg = _isolated_registry()
        # All specialists are on igpu_rocwmma — declare it UP
        fn = _health_fn(frozenset({"igpu_rocwmma"}))
        result = specialist_liveness_gaps(registry=reg, check_fleet_fn=fn)

        # Every registered specialist should be ready; gaps stay in lane_down
        ready_tasks = {r.task for r in result.ready}
        # At minimum: EXTRACTION, VISION, FUNCTION_CALL, RERANK must all be ready
        # (they are all on igpu_rocwmma and registered in the default registry)
        for task in (Task.EXTRACTION, Task.VISION, Task.FUNCTION_CALL, Task.RERANK):
            assert str(task) in ready_tasks, (
                f"{task}: igpu_rocwmma is UP but task not in ready — wrong partition"
            )

    def test_down_lane_puts_specialist_in_lane_down(self) -> None:
        """When all lanes are DOWN, every registered specialist goes to lane_down."""
        reg = _isolated_registry()
        fn = _health_fn(frozenset())  # no lanes UP
        result = specialist_liveness_gaps(registry=reg, check_fleet_fn=fn)

        assert result.ready == [], (
            f"all lanes DOWN → ready must be empty, got: {[r.task for r in result.ready]}"
        )
        assert len(result.lane_down) == len(SPECIALIST_TASKS)

    def test_gap_specialist_always_in_lane_down(self) -> None:
        """A Task with no registered model is always in lane_down, even if its lane is UP."""
        reg = _isolated_registry()
        # Remove OCR_DOC specialist → that Task becomes a gap
        ocr_ids = [m.model_id for m in reg.for_task(Task.OCR_DOC)]
        for mid in ocr_ids:
            reg.models.pop(mid)

        fn = _health_fn(frozenset({"igpu_rocwmma", "npu", "cpu"}))  # all lanes UP
        result = specialist_liveness_gaps(registry=reg, check_fleet_fn=fn)

        lane_down_tasks = {r.task for r in result.lane_down}
        assert str(Task.OCR_DOC) in lane_down_tasks, (
            "gap specialist must always land in lane_down even when lanes are UP"
        )
        ready_tasks = {r.task for r in result.ready}
        assert str(Task.OCR_DOC) not in ready_tasks, "gap cannot be ready"

    def test_partitions_are_disjoint(self) -> None:
        """ready ∩ lane_down must be empty."""
        reg = _isolated_registry()
        fn = _health_fn(frozenset({"igpu_rocwmma"}))
        result = specialist_liveness_gaps(registry=reg, check_fleet_fn=fn)

        ready_tasks = {r.task for r in result.ready}
        down_tasks = {r.task for r in result.lane_down}
        overlap = ready_tasks & down_tasks
        assert overlap == set(), f"partitions overlap: {overlap}"

    def test_partitions_cover_all_six_specialists(self) -> None:
        """Union of ready + lane_down must equal all 6 SPECIALIST_TASKS."""
        reg = _isolated_registry()
        fn = _health_fn(frozenset({"igpu_rocwmma"}))
        result = specialist_liveness_gaps(registry=reg, check_fleet_fn=fn)

        all_task_names = {str(t) for t in SPECIALIST_TASKS}
        covered = {r.task for r in result.ready} | {r.task for r in result.lane_down}
        assert covered == all_task_names, f"missing from coverage: {all_task_names - covered}"


class TestInjectionNotLive:
    """The injectable check_fleet_fn is always used — no live probe in tests."""

    def test_injected_fn_is_called(self) -> None:
        """Track that the injected function is invoked, not a live health probe."""
        call_log: list[str] = []

        def _recording_fn():
            call_log.append("called")
            lanes_dict = {"igpu_rocwmma": SimpleNamespace(status=SimpleNamespace(value="down"))}
            return SimpleNamespace(lanes=lanes_dict)

        reg = _isolated_registry()
        specialist_liveness_gaps(registry=reg, check_fleet_fn=_recording_fn)
        assert call_log == ["called"], (
            "check_fleet_fn must be called exactly once (injected, not the live prober)"
        )
