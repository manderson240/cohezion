"""Discriminating tests for the resource-aware router (user directive 2026-06-07).

`resource_aware_route` is the routing decision the fleet was missing: given a LIVE memory
snapshot + whether the interactive bot is busy + the task kind, decide whether there is room
to run and WHERE — or DEFER. Composes the K1/rule-5 OOM buffer (the gate triune uses at
available_gb<16), item-113 fleet-fairness (yield to the bot), item-114 placement
(interactive→iGPU / batch→NPU / deep→CPU). Report-only, pure (injected snapshot).

Each test fails a plausible wrong impl:
  - a "does it fit?" impl that ignores the OOM buffer → test_oom_buffer_dominates,
  - an impl that checks only the buffer and not per-task headroom → test_insufficient_headroom_defers,
  - an impl that ignores interactive_busy → test_busy_bot_yields_batch_to_npu,
  - an impl that hard-codes one engine → test_task_kind_picks_engine.
"""

from __future__ import annotations

from cohezion.competition.orchestrator.resource_guard import MemorySnapshot
from cohezion.inference.resource_aware_router import resource_aware_route


def _snap(available_gb: float) -> MemorySnapshot:
    return MemorySnapshot(total_gb=128.0, available_gb=available_gb, used_gb=128.0 - available_gb)


def test_oom_buffer_dominates() -> None:
    # available 8 GB < 16 GB buffer → DEFER, even though an 8 GB pool "fits" a 2 GB task.
    d = resource_aware_route(2.0, snapshot=_snap(8.0))
    assert d.action == "defer"
    assert "oom" in d.reason.lower()


def test_insufficient_headroom_defers() -> None:
    # 20 GB available is ABOVE the 16 GB buffer, but an 18 GB model needs 18*1.2=21.6 → DEFER.
    d = resource_aware_route(18.0, snapshot=_snap(20.0))
    assert d.action == "defer"
    assert "headroom" in d.reason.lower()


def test_busy_bot_yields_batch_to_npu() -> None:
    # Healthy memory, but the interactive bot is busy → a BATCH job yields to the NPU lane.
    d = resource_aware_route(2.0, snapshot=_snap(40.0), interactive_busy=True, task_kind="batch")
    assert d.action == "route"
    assert d.engine == "npu"
    assert "yield" in d.reason.lower()


def test_task_kind_picks_engine() -> None:
    snap = _snap(40.0)
    assert resource_aware_route(2.0, snapshot=snap, task_kind="interactive").engine == "igpu"
    assert resource_aware_route(2.0, snapshot=snap, task_kind="deep").engine == "cpu"
    assert resource_aware_route(2.0, snapshot=snap, task_kind="batch").engine == "npu"


def test_route_decision_is_reported_not_applied() -> None:
    # Report-only: a route decision carries action/engine/reason and nothing is loaded.
    d = resource_aware_route(2.0, snapshot=_snap(40.0), task_kind="interactive")
    assert d.action == "route"
    assert d.engine in {"npu", "igpu", "cpu"}
    assert isinstance(d.reason, str) and d.reason
