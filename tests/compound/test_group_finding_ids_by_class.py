"""Item 209: group_finding_ids_by_class() — class-to-ids reverse index (2026-06-08).

``group_finding_ids_by_class(problems: list[Problem])``
-> ``dict[str, list[str]]``:
Returns ``{problem_class: [finding_id, ...]}`` for all classes present in
*problems*, with keys in first-occurrence order and values in input order.
Empty list -> ``{}``.  Pure; no I/O.

Enables O(1) per-class id lookup vs the O(n) repeated ``finding_ids_for_class``
calls that item 208 requires::

    index = group_finding_ids_by_class(findings)
    # {"complexity_outlier": [...], "nesting_outlier": [...]}

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are lists of finding_id strings, not Problem objects.
     Kills an impl that stores the Problem instances instead of their ids.
  2. Keys are in first-occurrence order (not alphabetical or arbitrary).
     Kills an impl that sorts keys or relies on unordered dict iteration.
  3. Values are in input order for each class.
     Kills an impl that sorts ids within a class.
  4. Empty list -> {} (not raises).
     Kills an impl that raises on empty input.
  5. Classes with one entry are listed alongside multi-entry classes.
     Kills an impl that drops singleton classes or merges them into a default.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    group_finding_ids_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_values_are_strings_not_problem_objects() -> None:
    """Values are lists of finding_id strings, not Problem objects.

    PRIMARY DISCRIMINATOR: kills an impl that stores Problem instances
    instead of extracting their finding_id strings.
    """
    problems = [_p("complexity_outlier", 3)]

    result = group_finding_ids_by_class(problems)

    assert "complexity_outlier" in result
    ids = result["complexity_outlier"]
    assert len(ids) == 1
    assert isinstance(ids[0], str), "values must be str (finding_ids); got " + repr(type(ids[0]))
    assert ids[0] == "complexity_outlier:3", "must store the finding_id string; got " + repr(ids[0])


def test_keys_in_first_occurrence_order() -> None:
    """Keys appear in first-occurrence order, not alphabetical order.

    Kills an impl that sorts keys or uses a defaultdict with unordered
    iteration.  Here 'zeta' occurs before 'alpha' so it must appear first.
    """
    problems = [
        _p("zeta", 0),
        _p("alpha", 0),
        _p("zeta", 1),
    ]

    result = group_finding_ids_by_class(problems)

    keys = list(result.keys())
    assert keys == ["zeta", "alpha"], (
        "keys must be in first-occurrence order (zeta before alpha); got " + repr(keys)
    )


def test_values_in_input_order_per_class() -> None:
    """finding_ids within each class are in the same order as in problems.

    Kills an impl that sorts ids within a class or appends in reverse.
    Indices 2, 0, 1 for 'complexity_outlier' must appear in that order.
    """
    problems = [
        _p("complexity_outlier", 2),
        _p("nesting_outlier", 0),
        _p("complexity_outlier", 0),
        _p("complexity_outlier", 1),
    ]

    result = group_finding_ids_by_class(problems)

    assert result["complexity_outlier"] == [
        "complexity_outlier:2",
        "complexity_outlier:0",
        "complexity_outlier:1",
    ], "values must preserve input order; got " + repr(result["complexity_outlier"])


def test_empty_problems_returns_empty_dict() -> None:
    """Empty list -> {} (not raises).

    Kills an impl that raises IndexError or returns a non-empty default.
    """
    result = group_finding_ids_by_class([])

    assert result == {}, "empty input must return {}; got " + repr(result)


def test_singleton_and_multi_classes_coexist() -> None:
    """Classes with one entry and multi-entry classes both appear in result.

    Kills an impl that silently drops classes with only one finding or merges
    them into a catch-all bucket.
    """
    problems = [
        _p("alpha", 0),  # singleton
        _p("beta", 0),
        _p("beta", 1),  # two entries
        _p("gamma", 0),  # singleton
    ]

    result = group_finding_ids_by_class(problems)

    assert set(result.keys()) == {"alpha", "beta", "gamma"}, (
        "all three classes must be present; got " + repr(list(result.keys()))
    )
    assert result["alpha"] == ["alpha:0"], repr(result["alpha"])
    assert result["beta"] == ["beta:0", "beta:1"], repr(result["beta"])
    assert result["gamma"] == ["gamma:0"], repr(result["gamma"])
