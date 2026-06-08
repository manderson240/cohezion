"""Item 129: memory_gap_priority — TDD red→green (2026-06-08).

``memory_gap_priority(store, routing_records, *, task_classes)`` ranks gap
task_classes (those with NO cerebellum memory — item-75) by how often the
fleet routes them. The most-routed UNREMEMBERED task is the highest-value
memory to grow first.

Returns ``[(task_class, route_count)]`` descending by count. Gaps never
routed are excluded. Covered tasks (not gaps) are excluded even if routed.
Composes item-75 ``memory_gaps`` + routing_records shape.

Discriminating tests — each kills a plausible wrong implementation:

  1. High-count gap ranks above low-count gap    (PRIMARY DISC.: kills "alphabetical sort")
  2. Covered task excluded even if routed often  (kills "rank all routed tasks")
  3. Gap never routed is excluded                (kills "return all gaps with count 0")
  4. Empty inputs → []                           (kills impl that raises)
  5. Result is sorted descending                 (kills "sorted ascending")
"""

from __future__ import annotations

from cohezion.governance.memory_gap_priority import memory_gap_priority


def _store_with(task_classes: list[str]) -> list[dict]:
    """Build a minimal cerebellum store covering the given task_classes."""
    return [
        {
            "country": "cerebellum",
            "name": f"cerebellum:{tc}->npu",
            "tags": ["cerebellum", tc, "npu", "npu"],
        }
        for tc in task_classes
    ]


def _routing(task_class: str, n: int = 1) -> list[dict]:
    return [{"task_class": task_class, "lane": "npu", "fell_back": False} for _ in range(n)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_high_count_gap_ranks_above_low_count() -> None:
    """A gap routed 10× ranks above a gap routed 2×.

    PRIMARY DISCRIMINATOR: kills an impl that sorts alphabetically or
    returns gaps in insertion order.
    """
    store = _store_with(["CODE_GEN"])  # CODE_GEN is COVERED; RERANK and EMBED are gaps
    records = _routing("RERANK", n=10) + _routing("EMBED", n=2)
    result = memory_gap_priority(store, records, task_classes=["CODE_GEN", "RERANK", "EMBED"])
    task_classes = [tc for tc, _ in result]
    assert task_classes[0] == "RERANK", f"RERANK (10×) must rank first; got {result}"
    assert task_classes[1] == "EMBED", f"EMBED (2×) must rank second; got {result}"


def test_covered_task_excluded_even_if_routed_often() -> None:
    """A covered task (has a stored neuron) is excluded even if routed 100×.

    Kills an impl that ranks all routed tasks (covered + gaps alike).
    """
    store = _store_with(["COVERED"])  # COVERED has a stored neuron → not a gap
    records = _routing("COVERED", n=100) + _routing("GAP", n=5)
    result = memory_gap_priority(store, records, task_classes=["COVERED", "GAP"])
    task_classes = [tc for tc, _ in result]
    assert "COVERED" not in task_classes, f"COVERED (not a gap) must be excluded; got {result}"
    assert "GAP" in task_classes, f"GAP must appear; got {result}"


def test_gap_never_routed_excluded() -> None:
    """A gap task with 0 routing records is excluded from the result.

    Kills an impl that returns all gaps including never-routed ones.
    """
    store = _store_with([])  # empty store → RERANK and EMBED both gaps
    records = _routing("RERANK", n=5)  # EMBED never routed
    result = memory_gap_priority(store, records, task_classes=["RERANK", "EMBED"])
    task_classes = [tc for tc, _ in result]
    assert "RERANK" in task_classes, f"RERANK (5 routes) must appear; got {result}"
    assert "EMBED" not in task_classes, f"EMBED (0 routes) must be excluded; got {result}"


def test_empty_inputs_returns_empty() -> None:
    """Empty store and empty records → empty result (no crash)."""
    result = memory_gap_priority([], [], task_classes=["RERANK"])
    assert result == [], f"empty inputs must → []; got {result}"


def test_result_sorted_descending() -> None:
    """Result is sorted by route_count descending (highest priority first).

    Kills an impl that sorts ascending.
    """
    store = _store_with([])  # all three are gaps
    records = _routing("A", n=3) + _routing("B", n=7) + _routing("C", n=1)
    result = memory_gap_priority(store, records, task_classes=["A", "B", "C"])
    counts = [count for _, count in result]
    assert counts == sorted(counts, reverse=True), (
        f"result must be sorted descending by count; got {result}"
    )
    assert result[0] == ("B", 7), f"B (7×) must be first; got {result}"
