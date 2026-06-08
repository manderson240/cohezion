"""Item 126: cerebellum_drift_all — TDD red→green (2026-06-08).

``cerebellum_drift_all(records, *, store)`` sweeps EVERY stabilized task_class in the
routing corpus and returns ALL whose current lane contradicts their stored cerebellum neuron.
Composes item-72 ``cerebellum_drift`` logic per-class by grouping records by task_class.

Discriminating tests — each kills a plausible wrong implementation:

  1. Two drifted classes → BOTH reported       (PRIMARY DISC.: kills item-72 single-strongest)
  2. One drifted + one stable → only drifted   (kills "return all with stored neurons")
  3. No stored neuron → excluded (novel)       (kills "return all stable patterns")
  4. No stable class → []                      (kills an impl that raises on empty)
  5. Result is a list, not a single tuple      (kills "return the first/only drift")
"""

from __future__ import annotations

from cohezion.governance.cerebellum_drift_all import cerebellum_drift_all
from cohezion.governance.knowledge_bridge import build_cerebellum_neuron


def _records(task_class: str, lane: str, n: int = 6) -> list[dict]:
    return [{"task_class": task_class, "lane": lane, "fell_back": False} for _ in range(n)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_two_drifted_classes_both_reported() -> None:
    """Two task_classes both drifted → BOTH appear in the result.

    PRIMARY DISCRIMINATOR: kills item-72's single-strongest impl which would
    only surface one drift (the strongest by consistency × samples).
    """
    store = [
        build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10),
        build_cerebellum_neuron("CLASSIFY", "npu", consistency=0.9, samples=10),
    ]
    records = _records("RERANK", "cpu") + _records("CLASSIFY", "igpu")
    result = cerebellum_drift_all(records, store=store)
    task_classes = {tc for tc, _, _ in result}
    assert "RERANK" in task_classes, f"RERANK drift must be reported; got {result}"
    assert "CLASSIFY" in task_classes, f"CLASSIFY drift must be reported; got {result}"


def test_one_drifted_one_stable_only_drifted_reported() -> None:
    """One class drifted, one stable → only the drifted one is in the result.

    Kills an impl that returns all task_classes with stored neurons regardless
    of whether their current lane matches.
    """
    store = [
        build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10),
        build_cerebellum_neuron("CLASSIFY", "npu", consistency=0.9, samples=10),
    ]
    # RERANK now routes to cpu (drift from stored igpu)
    # CLASSIFY still routes to npu (matches stored npu — no drift)
    records = _records("RERANK", "cpu") + _records("CLASSIFY", "npu")
    result = cerebellum_drift_all(records, store=store)
    task_classes = {tc for tc, _, _ in result}
    assert "RERANK" in task_classes, f"RERANK (drifted) must appear; got {result}"
    assert "CLASSIFY" not in task_classes, f"CLASSIFY (stable) must NOT appear; got {result}"


def test_no_stored_neuron_excluded() -> None:
    """A newly-stabilized class with no stored cerebellum neuron is NOVEL, not drift.

    Kills an impl that returns every stable pattern regardless of whether a stored
    neuron exists for comparison.
    """
    result = cerebellum_drift_all(_records("RERANK", "cpu"), store=[])
    assert result == [], f"novel stabilization (no stored) must → []; got {result}"


def test_no_stable_class_returns_empty() -> None:
    """All records are noisy (fell_back) → no stable pattern → empty result.

    Kills an impl that raises ZeroDivisionError or KeyError on noise-only records.
    """
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10)]
    noisy = [{"task_class": "RERANK", "lane": f"lane{i}", "fell_back": True} for i in range(6)]
    result = cerebellum_drift_all(noisy, store=store)
    assert result == [], f"noisy records → no stable pattern → []; got {result}"


def test_result_is_list_of_triples() -> None:
    """Result is a list of (task_class, old_lane, new_lane) triples, not a single tuple.

    Kills an impl that returns the raw cerebellum_drift single-result tuple.
    """
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=0.9, samples=10)]
    result = cerebellum_drift_all(_records("RERANK", "cpu"), store=store)
    assert isinstance(result, list), f"must return list; got {type(result)}"
    assert len(result) == 1
    assert result[0] == ("RERANK", "igpu", "cpu"), f"triple mismatch; got {result[0]}"
