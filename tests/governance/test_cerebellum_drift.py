"""Discriminating tests for cerebellum_drift (backlog item 72, 2026-06-07).

A STORED cerebellum neuron (procedural routing memory) goes STALE when the fleet's optimal
lane for a task_class changes. `cerebellum_drift(records, *, store)` flags it: current stable
lane != stored lane → `(task_class, old_lane, new_lane)`; else None. Report-only; composes
item-24 `_detect_stable_routing_pattern` + item-29 `recall_neurons`.

Each test fails a plausible wrong impl:
  - an impl that ignores the stored lane → test_drift_detected (must report old AND new),
  - an impl that flags on any stored neuron → test_same_lane_no_drift,
  - an impl that treats a novel pattern as drift → test_no_stored_is_novel_not_drift,
  - an impl that reports on noise → test_no_stable_pattern.
"""

from __future__ import annotations

from cohezion.governance.cerebellum_drift import cerebellum_drift
from cohezion.governance.knowledge_bridge import build_cerebellum_neuron


def _records(task_class: str, lane: str, n: int = 6) -> list[dict]:
    return [{"task_class": task_class, "lane": lane, "fell_back": False} for _ in range(n)]


def test_drift_detected() -> None:
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10)]
    # records now stabilize on a DIFFERENT lane (cpu) → drift from the stored igpu.
    drift = cerebellum_drift(_records("RERANK", "cpu"), store=store)
    assert drift == ("RERANK", "igpu", "cpu")


def test_same_lane_no_drift() -> None:
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10)]
    # records stabilize on the SAME lane as stored → no drift.
    assert cerebellum_drift(_records("RERANK", "igpu"), store=store) is None


def test_no_stored_is_novel_not_drift() -> None:
    # A stable pattern with NO stored cerebellum neuron is novel, not drift.
    assert cerebellum_drift(_records("RERANK", "cpu"), store=[]) is None


def test_no_stable_pattern() -> None:
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10)]
    # noisy records (every decision a different lane, all fell back) → no stable pattern → None.
    noisy = [{"task_class": "RERANK", "lane": f"lane{i}", "fell_back": True} for i in range(6)]
    assert cerebellum_drift(noisy, store=store) is None


# ── item 126: multi-class drift sweep (item-72 surfaces only the strongest class) ──
from cohezion.governance.cerebellum_drift import cerebellum_drift_all


def test_both_drifted_classes_reported() -> None:
    # DISCRIMINATING: TWO classes drift; item-72 (single strongest) reports only one.
    store = [
        build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10),
        build_cerebellum_neuron("SUMMARIZE", "npu", consistency=0.9, samples=10),
    ]
    records = _records("RERANK", "cpu") + _records("SUMMARIZE", "igpu")
    out = cerebellum_drift_all(records, store=store)
    assert out == [("RERANK", "igpu", "cpu"), ("SUMMARIZE", "npu", "igpu")]


def test_only_drifted_class_reported() -> None:
    store = [
        build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10),
        build_cerebellum_neuron("SUMMARIZE", "igpu", consistency=0.9, samples=10),
    ]
    # RERANK drifts to cpu; SUMMARIZE stays on igpu → only RERANK reported.
    records = _records("RERANK", "cpu") + _records("SUMMARIZE", "igpu")
    assert cerebellum_drift_all(records, store=store) == [("RERANK", "igpu", "cpu")]


def test_novel_class_excluded_from_sweep() -> None:
    # RERANK drifts; SUMMARIZE has NO stored neuron (novel) → excluded.
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10)]
    records = _records("RERANK", "cpu") + _records("SUMMARIZE", "igpu")
    assert cerebellum_drift_all(records, store=store) == [("RERANK", "igpu", "cpu")]


def test_no_stable_class_sweep_empty() -> None:
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10)]
    # 1 sample < min_samples → no stable pattern → []
    assert cerebellum_drift_all([{"task_class": "RERANK", "lane": "cpu"}], store=store) == []
