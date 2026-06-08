"""Item 192: filter_by_class() — class-domain keep filter (2026-06-08).

``filter_by_class(problems: list[Problem], keep_classes: frozenset[str])``
→ ``list[Problem]``:
Returns only the findings whose ``problem_class`` is in *keep_classes*,
in insertion order.  Empty *keep_classes* → ``[]``.  Pure; no I/O.

Symmetric dual of :func:`exclude_problems` (removes by ID) — this one
KEEPS by class::

    filter_by_class(findings, frozenset({"complexity_outlier"}))

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: non-matching keep_classes → empty list.
     Kills a no-op impl that returns all findings regardless of keep_classes.
  2. Matching class → only those findings returned (others excluded).
     Kills an impl that returns all findings even when some don't match.
  3. Empty keep_classes → [] (no raises).
     Kills an impl that treats empty keep_classes as "keep all".
  4. Insertion order of kept findings preserved.
     Kills an impl that sorts the result or reverses it.
  5. Empty problems → [] (no raises).
     Kills an impl that raises IndexError on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    filter_by_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_non_matching_keep_classes_returns_empty() -> None:
    """keep_classes with no matching findings → empty list.

    PRIMARY DISCRIMINATOR: kills a no-op impl that returns all findings
    unchanged (ignoring the keep_classes argument).
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]
    keep_classes = frozenset({"long_function"})  # not in problems

    result = filter_by_class(problems, keep_classes)

    assert result == [], f"No-match keep_classes must return []; got {result!r}"


def test_matching_class_returns_only_those_findings() -> None:
    """keep_classes matches one class → only that class's findings returned.

    Kills an impl that returns all findings even when some don't match
    the keep_classes filter.
    """
    problems = [
        _p("complexity_outlier"),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
    ]
    keep_classes = frozenset({"complexity_outlier"})

    result = filter_by_class(problems, keep_classes)

    fids = [p.finding_id for p in result]
    assert "nesting_outlier:0" not in fids, f"nesting_outlier must be excluded; got {fids!r}"
    assert len(result) == 2, (
        f"Two complexity_outlier findings must be returned; got {len(result)}: {fids!r}"
    )


def test_empty_keep_classes_returns_empty_list() -> None:
    """Empty keep_classes → [] (not all findings).

    Kills an impl that treats empty frozenset as "keep all" instead of
    "keep nothing" — the empty set matches nothing, so result is empty.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = filter_by_class(problems, frozenset())

    assert result == [], f"Empty keep_classes must return []; got {result!r}"


def test_insertion_order_of_kept_findings_preserved() -> None:
    """Kept findings appear in their original insertion order.

    Kills an impl that sorts the result or returns findings in a different
    order than they appeared in the input list.
    """
    problems = [
        _p("complexity_outlier", 2),
        _p("nesting_outlier"),
        _p("complexity_outlier", 0),
        _p("complexity_outlier", 1),
    ]
    keep_classes = frozenset({"complexity_outlier"})

    result = filter_by_class(problems, keep_classes)

    fids = [p.finding_id for p in result]
    assert fids == [
        "complexity_outlier:2",
        "complexity_outlier:0",
        "complexity_outlier:1",
    ], f"Insertion order must be preserved; got {fids!r}"


def test_empty_problems_returns_empty() -> None:
    """Empty problems list → [] regardless of keep_classes.

    Kills an impl that raises IndexError on empty input.
    """
    result = filter_by_class([], frozenset({"complexity_outlier"}))

    assert result == [], f"Empty problems must return []; got {result!r}"
