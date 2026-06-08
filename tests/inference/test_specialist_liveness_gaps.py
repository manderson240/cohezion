"""Discriminating tests for specialist_liveness_gaps (backlog item 77, 2026-06-08).

`specialist_liveness_gaps(*, registry, check_fleet_fn)` ties item-38 specialist coverage to LIVE
lane health (the same `health.lanes[key].status.value == "up"` contract `audit_liveness` uses):
partition registered specialists into `ready` (lane UP → a verification attempt is possible now)
vs `lane_down` (lane not UP → can't test now, explains the stuck 0/6 campaign). Report-only.

Uses a REAL isolated FleetRegistry (the object the production path constructs) + an injected
health fn — so no live probe under pytest, and lanes are derived dynamically (robust to lane
reassignment). Each test fails a plausible wrong impl:
  - an impl that ignores lane health → test_all_lanes_down_all_lane_down,
  - an impl keying on `verified_working` not lane liveness → test_ready_is_attemptability_not_history,
  - an impl that buckets gap Tasks (no model) → test_gap_task_in_neither_partition,
  - an impl with a hidden live probe → test_injected_health_determines_result.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace

from cohezion.inference.registry import FleetRegistry, Task, get_registry
from cohezion.inference.specialist_coverage import (
    SPECIALIST_TASKS,
    specialist_liveness_gaps,
)


def _isolated_registry() -> FleetRegistry:
    # Mirror the existing specialist_coverage tests: a real registry, deep-copied so mutation
    # here never leaks into the module singleton.
    return FleetRegistry(models=copy.deepcopy(get_registry().models))


def _health(status_by_lane: dict[str, str]) -> SimpleNamespace:
    # Mirrors the live check_fleet() shape: health.lanes[lane_value].status.value.
    lanes = {
        lane: SimpleNamespace(status=SimpleNamespace(value=status))
        for lane, status in status_by_lane.items()
    }
    return SimpleNamespace(lanes=lanes)


def _preferred_lane(reg: FleetRegistry, task: Task) -> str | None:
    cands = reg.for_task(task)
    return cands[0].lane.value if cands else None


def _registered(reg: FleetRegistry) -> set[str]:
    return {str(t) for t in SPECIALIST_TASKS if reg.for_task(t)}


def _all_lanes(reg: FleetRegistry, status: str) -> dict[str, str]:
    return {lane: status for t in SPECIALIST_TASKS if (lane := _preferred_lane(reg, t)) is not None}


def test_all_lanes_up_all_registered_ready() -> None:
    reg = _isolated_registry()
    out = specialist_liveness_gaps(
        registry=reg, check_fleet_fn=lambda: _health(_all_lanes(reg, "up"))
    )
    assert set(out.ready) == _registered(reg)
    assert out.lane_down == []


def test_all_lanes_down_all_lane_down() -> None:
    # DISCRIMINATING: an impl that ignores lane health (everything ready) fails this.
    reg = _isolated_registry()
    out = specialist_liveness_gaps(
        registry=reg, check_fleet_fn=lambda: _health(_all_lanes(reg, "down"))
    )
    assert set(out.lane_down) == _registered(reg)
    assert out.ready == []


def test_ready_is_attemptability_not_history() -> None:
    # DISCRIMINATING: the live registry is 0/6 serving-verified, yet with all lanes UP every
    # registered specialist is READY (a verification ATTEMPT is possible). An impl keying on
    # verified_working would (wrongly) put all of them in lane_down.
    reg = _isolated_registry()
    report_unverified = [
        t for t in SPECIALIST_TASKS if reg.for_task(t) and not reg.for_task(t)[0].verified_working
    ]
    assert report_unverified, "precondition: at least one registered-but-unverified specialist"
    out = specialist_liveness_gaps(
        registry=reg, check_fleet_fn=lambda: _health(_all_lanes(reg, "up"))
    )
    for t in report_unverified:
        assert str(t) in out.ready


def test_unknown_lane_is_lane_down() -> None:
    # A lane absent from the health report → "unknown" → not testable now.
    reg = _isolated_registry()
    out = specialist_liveness_gaps(registry=reg, check_fleet_fn=lambda: _health({}))
    assert set(out.lane_down) == _registered(reg)
    assert out.ready == []


def test_gap_task_in_neither_partition() -> None:
    # DISCRIMINATING: a specialist Task with NO model (for_task=[]) is a coverage gap — it must be
    # in NEITHER partition. An impl that buckets all SPECIALIST_TASKS would include it in lane_down.
    reg = _isolated_registry()
    ocr = reg.for_task(Task.OCR_DOC)
    if not ocr:
        return  # nothing to make a gap from; skip silently
    del reg.models[ocr[0].model_id]
    assert reg.for_task(Task.OCR_DOC) == []  # now a genuine gap
    out = specialist_liveness_gaps(
        registry=reg, check_fleet_fn=lambda: _health(_all_lanes(reg, "up"))
    )
    assert str(Task.OCR_DOC) not in out.ready
    assert str(Task.OCR_DOC) not in out.lane_down


def test_partitions_disjoint_and_cover_registered() -> None:
    reg = _isolated_registry()
    # Mark roughly half the lanes up, half down (deterministic by sorted lane name).
    lanes = sorted(set(_all_lanes(reg, "up")))
    mixed = {lane: ("up" if i % 2 == 0 else "down") for i, lane in enumerate(lanes)}
    out = specialist_liveness_gaps(registry=reg, check_fleet_fn=lambda: _health(mixed))
    assert set(out.ready).isdisjoint(out.lane_down)
    assert set(out.ready) | set(out.lane_down) == _registered(reg)


def test_injected_health_determines_result() -> None:
    # DISCRIMINATING: flipping ONLY the injected health flips the buckets → no hidden live probe.
    reg = _isolated_registry()
    up = specialist_liveness_gaps(
        registry=reg, check_fleet_fn=lambda: _health(_all_lanes(reg, "up"))
    )
    down = specialist_liveness_gaps(
        registry=reg, check_fleet_fn=lambda: _health(_all_lanes(reg, "down"))
    )
    assert set(up.ready) == _registered(reg) and up.lane_down == []
    assert set(down.lane_down) == _registered(reg) and down.ready == []
