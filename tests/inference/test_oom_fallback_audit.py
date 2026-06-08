"""Discriminating tests for oom_fallback_gaps (backlog item 146, 2026-06-08).

Structural audit generalizing item 144: a Task whose preferred iGPU model is LARGE should NOT
silently fall to CPU/cloud under memory pressure when a smaller iGPU model could serve it. The
audit flags Tasks where the preferred large iGPU model has no smaller iGPU fallback. Report-only.

Each test fails a plausible wrong impl:
  - an impl that ignores the smaller-iGPU check → test_covered_when_smaller_igpu_exists,
  - an impl that flags any large model regardless of an iGPU fallback → same,
  - an impl that fabricates a size for size_gb=None → test_unknown_size_not_fabricated.
"""

from __future__ import annotations

from types import SimpleNamespace

from cohezion.inference.oom_fallback_audit import oom_fallback_gaps
from cohezion.inference.registry import Lane, Task, get_registry


def _c(lane: Lane, size: float | None) -> SimpleNamespace:
    return SimpleNamespace(lane=lane, size_gb=size)


class _FakeReg:
    def __init__(self, by_task: dict) -> None:
        self._by_task = by_task

    def for_task(self, task: Task) -> list:
        return self._by_task.get(task, [])


def test_gap_flagged_when_no_smaller_igpu() -> None:
    # large iGPU (15GB) preferred, only a CPU fallback below it → OOM-fallback gap.
    reg = _FakeReg({Task.CODE_GEN: [_c(Lane.IGPU_ROCWMMA, 15.0), _c(Lane.CPU, 8.0)]})
    assert Task.CODE_GEN in oom_fallback_gaps(reg)


def test_covered_when_smaller_igpu_exists() -> None:
    # DISCRIMINATING: a smaller iGPU model (6GB) below the 15GB → NOT a gap (item-144 fix).
    # An impl ignoring the smaller-iGPU check would still flag it.
    reg = _FakeReg(
        {
            Task.CODE_GEN: [
                _c(Lane.IGPU_ROCWMMA, 15.0),
                _c(Lane.IGPU_ROCWMMA, 6.0),
                _c(Lane.CPU, 8.0),
            ]
        }
    )
    assert Task.CODE_GEN not in oom_fallback_gaps(reg)


def test_small_preferred_not_flagged() -> None:
    # preferred iGPU model is small (< threshold) → no OOM risk → not flagged.
    reg = _FakeReg({Task.CODE_GEN: [_c(Lane.IGPU_ROCWMMA, 5.0), _c(Lane.CPU, 8.0)]})
    assert oom_fallback_gaps(reg) == []


def test_unknown_size_not_fabricated() -> None:
    # preferred has size_gb=None → never treated as large (no fabrication).
    reg = _FakeReg({Task.CODE_GEN: [_c(Lane.IGPU_ROCWMMA, None), _c(Lane.CPU, 8.0)]})
    assert oom_fallback_gaps(reg) == []


def test_live_registry_runs_and_code_gen_covered() -> None:
    # Non-fabricated live check: runs over the real registry; CODE_GEN is covered post-item-144.
    gaps = oom_fallback_gaps(get_registry())
    assert isinstance(gaps, list)
    assert Task.CODE_GEN not in gaps
