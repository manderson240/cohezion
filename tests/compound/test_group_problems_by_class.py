"""Item 176: group_problems_by_class() — findings grouped by class (2026-06-08).

``group_problems_by_class(problems: list[Problem])`` → ``dict[str, list[Problem]]``:
Groups findings by ``problem_class`` so callers can access the actual ``finding_id``
values per class (not just counts).

Structural complement of :func:`problem_count_by_class` (item 160): where that
function returns ``{class: int}``, this one returns ``{class: [Problem, ...]}``.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: mixed-class list → each class key maps to exactly the
     Problem instances of that class (not to the count int).
     Kills an impl that returns ``{class: count}`` instead of ``{class: [...]}``.
  2. Empty input → ``{}``.
     Kills an impl that returns ``{"": []}`` or raises on empty input.
  3. Single-class input → ``{cls: all_findings}``.
     Kills an impl that truncates the list to 1 element.
  4. Finding order within each group matches input order.
     Kills an impl that sorts within groups (order must be preserved).
  5. Each group contains Problem instances (not finding_id strings).
     Kills an impl that stores strings instead of typed Problem objects.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    group_problems_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_each_key_maps_to_problem_list_not_count() -> None:
    """Mixed-class list → each class key maps to [Problem, ...] not int count.

    PRIMARY DISCRIMINATOR: kills an impl that maps class → count (like
    problem_count_by_class does) instead of class → actual Problem list.
    """
    problems = [_p("alpha"), _p("beta"), _p("alpha", 1)]

    result = group_problems_by_class(problems)

    assert "alpha" in result, f"'alpha' class must be a key; got {list(result.keys())!r}"
    assert isinstance(result["alpha"], list), (
        f"Each value must be a list; got {type(result['alpha'])} for 'alpha'"
    )
    assert len(result["alpha"]) == 2, f"'alpha' must have 2 findings; got {len(result['alpha'])}"
    assert len(result["beta"]) == 1, f"'beta' must have 1 finding; got {len(result['beta'])}"


def test_empty_input_returns_empty_dict() -> None:
    """Empty problems list → empty dict (no raises, no phantom keys).

    Kills an impl that returns {"":[]} or raises IndexError on empty input.
    """
    result = group_problems_by_class([])

    assert result == {}, f"Empty input must return {{}}; got {result!r}"


def test_single_class_all_findings_in_group() -> None:
    """Single-class input → {cls: [all 3 findings]}.

    Kills an impl that truncates the list to the first element only.
    """
    problems = [_p("nesting_outlier", i) for i in range(3)]

    result = group_problems_by_class(problems)

    assert list(result.keys()) == ["nesting_outlier"], (
        f"Only one class expected; got {list(result.keys())!r}"
    )
    assert len(result["nesting_outlier"]) == 3, (
        f"All 3 findings must be in the group; got {len(result['nesting_outlier'])}"
    )


def test_finding_order_preserved_within_group() -> None:
    """Group elements are in input order (not sorted).

    Kills an impl that sorts within groups (which would break the TIDE
    ordering guarantee used by downstream reporting).
    """
    # Deliberately insert in non-alphabetical finding_id order
    p0 = Problem(problem_class="complexity_outlier", finding_id="complexity_outlier:z.py:99")
    p1 = Problem(problem_class="complexity_outlier", finding_id="complexity_outlier:a.py:1")
    problems = [p0, p1]

    result = group_problems_by_class(problems)

    group = result["complexity_outlier"]
    assert group[0].finding_id == "complexity_outlier:z.py:99", (
        f"First finding in group must preserve input order; got {group[0].finding_id!r}"
    )
    assert group[1].finding_id == "complexity_outlier:a.py:1", (
        f"Second finding in group must preserve input order; got {group[1].finding_id!r}"
    )


def test_group_values_are_problem_instances() -> None:
    """Each group contains Problem instances, not raw strings.

    Kills an impl that stores finding_id strings instead of typed Problem objects.
    """
    problems = [_p("long_function")]

    result = group_problems_by_class(problems)

    group = result["long_function"]
    assert len(group) == 1
    assert isinstance(group[0], Problem), (
        f"Group elements must be Problem instances; got {type(group[0])}"
    )
    assert group[0].finding_id == "long_function:0", (
        f"Problem finding_id must be preserved; got {group[0].finding_id!r}"
    )
