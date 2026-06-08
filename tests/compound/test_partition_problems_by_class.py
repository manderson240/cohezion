"""Item 193: partition_problems_by_class() — two-way partition (2026-06-08).

``partition_problems_by_class(problems, target_classes: frozenset[str])``
→ ``tuple[list[Problem], list[Problem]]``:
Returns ``(matched, rest)`` where ``matched`` contains findings whose
``problem_class`` is in *target_classes* and ``rest`` contains all others.
Both partitions are in original insertion order.
Empty *target_classes* → ``([], all_problems)``.  Pure; no I/O.

Avoids two-pass filtering for callers who need both halves::

    matched, rest = partition_problems_by_class(
        findings, frozenset({"complexity_outlier"})
    )

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: matched + rest == original (no losses, no duplicates).
     Kills an impl that loses findings or duplicates them across partitions.
  2. Non-matching target_classes → ([], all_problems).
     Kills an impl that puts everything in matched (no-op).
  3. Empty target_classes → ([], all_problems).
     Kills an impl that treats empty target_classes as "match all".
  4. Insertion order preserved in each partition.
     Kills an impl that sorts within partitions.
  5. Return type is tuple (not list-of-lists).
     Kills an impl that returns a list[list[Problem]] instead of a tuple.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    partition_problems_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_matched_plus_rest_equals_original() -> None:
    """matched + rest reconstructs the original list with no losses.

    PRIMARY DISCRIMINATOR: kills an impl that drops findings (e.g. if a
    finding is in neither partition) or duplicates them (e.g. puts the same
    finding in both partitions).
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
        _p("long_function"),
    ]
    target_classes = frozenset({"complexity_outlier"})

    matched, rest = partition_problems_by_class(problems, target_classes)

    # Reconstruction must equal original (order within each partition is preserved
    # but the two partitions are interleaved in the original).
    combined_ids = [p.finding_id for p in matched] + [p.finding_id for p in rest]
    matched_ids = {p.finding_id for p in matched}
    rest_ids = {p.finding_id for p in rest}
    original_ids = {p.finding_id for p in problems}

    assert matched_ids | rest_ids == original_ids, (
        f"matched ∪ rest must equal original; missing: {original_ids - (matched_ids | rest_ids)!r}"
    )
    assert matched_ids & rest_ids == set(), (
        f"matched ∩ rest must be empty (no duplicates); overlap: {matched_ids & rest_ids!r}"
    )
    assert len(combined_ids) == len(problems), (
        f"Total count must equal original; got {len(combined_ids)} vs {len(problems)}"
    )


def test_non_matching_target_returns_empty_matched() -> None:
    """target_classes not in problems → ([], all_problems).

    Kills an impl that always puts everything in matched (no-op).
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]
    target_classes = frozenset({"long_function"})  # not in problems

    matched, rest = partition_problems_by_class(problems, target_classes)

    assert matched == [], f"No match → matched must be []; got {matched!r}"
    assert len(rest) == 2, f"All findings in rest; got {len(rest)}: {rest!r}"


def test_empty_target_classes_puts_all_in_rest() -> None:
    """Empty target_classes → ([], all_problems).

    Kills an impl that treats empty frozenset as "match all" instead of
    "match nothing" — empty set matches nothing.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    matched, rest = partition_problems_by_class(problems, frozenset())

    assert matched == [], f"Empty target_classes → matched=[]; got {matched!r}"
    assert len(rest) == 2, f"All findings in rest; got {len(rest)}: {rest!r}"


def test_insertion_order_preserved_in_each_partition() -> None:
    """Each partition preserves the insertion order of findings from the original.

    Kills an impl that sorts within partitions.
    """
    problems = [
        _p("complexity_outlier", 2),
        _p("nesting_outlier", 1),
        _p("complexity_outlier", 0),
        _p("nesting_outlier", 0),
    ]
    target_classes = frozenset({"complexity_outlier"})

    matched, rest = partition_problems_by_class(problems, target_classes)

    assert [p.finding_id for p in matched] == [
        "complexity_outlier:2",
        "complexity_outlier:0",
    ], f"Matched insertion order wrong; got {[p.finding_id for p in matched]!r}"
    assert [p.finding_id for p in rest] == [
        "nesting_outlier:1",
        "nesting_outlier:0",
    ], f"Rest insertion order wrong; got {[p.finding_id for p in rest]!r}"


def test_return_type_is_tuple() -> None:
    """Return value is a tuple, not a list-of-lists.

    Kills an impl that returns list[list[Problem]] instead of
    tuple[list[Problem], list[Problem]].
    """
    result = partition_problems_by_class(
        [_p("complexity_outlier")], frozenset({"complexity_outlier"})
    )

    assert isinstance(result, tuple), f"Return type must be tuple; got {type(result)}"
    assert len(result) == 2, f"Tuple must have exactly 2 elements; got {len(result)}"
