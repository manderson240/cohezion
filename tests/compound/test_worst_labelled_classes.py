"""Item 295: worst_labelled_classes() — classes ranked by labelling coverage ascending (2026-06-08).

``worst_labelled_classes(problems: list[Problem]) -> list[tuple[str, float]]``:
Returns list of (class, coverage) sorted by coverage ascending (worst first).
Ties broken by class name ascending. Empty -> []. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: lowest-coverage class appears first (ascending order).
     Kills impl sorted descending (best first).
  2. Tie-break by class name ascending.
     Kills impl with unstable or reversed tie-breaking.
  3. Classes with 0.0 coverage appear before partial-coverage classes.
     Verifies 0.0 sorts correctly.
  4. Empty input -> [].
     Kills impl raising on empty.
  5. Return is list[tuple[str, float]] — two-element tuples.
     Kills impl returning dict or three-element tuples.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    worst_labelled_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    """Unlabelled problem (severity='')."""
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_lowest_coverage_first() -> None:
    """Lowest-coverage class appears first in result.

    PRIMARY DISCRIMINATOR: kills impl sorted descending.
    alpha: 0/2 = 0.0; beta: 1/2 = 0.5; gamma: 2/2 = 1.0.
    Expected order: alpha (0.0), beta (0.5), gamma (1.0).
    """
    problems = [
        _p("alpha", 0),             # unlabelled
        _p("alpha", 1),             # unlabelled
        _ps("beta", 0, "HIGH"),     # labelled
        _p("beta", 1),              # unlabelled
        _ps("gamma", 0, "HIGH"),    # labelled
        _ps("gamma", 1, "LOW"),     # labelled
    ]
    result = worst_labelled_classes(problems)
    assert result[0][0] == "alpha", (
        "alpha (0.0) is worst -> first; got " + repr(result)
    )
    assert abs(result[0][1] - 0.0) < 1e-9, (
        "alpha coverage 0.0; got " + repr(result[0][1])
    )
    assert result[-1][0] == "gamma", (
        "gamma (1.0) is best -> last; got " + repr(result)
    )


def test_tie_break_by_class_name_ascending() -> None:
    """Equal-coverage classes are sorted by class name ascending.

    Kills impl with unstable or reversed tie-breaking.
    'zebra' and 'alpha' both 0.5; 'alpha' < 'zebra' -> alpha first.
    """
    problems = [
        _ps("zebra", 0, "HIGH"),
        _p("zebra", 1),
        _ps("alpha", 0, "HIGH"),
        _p("alpha", 1),
    ]
    result = worst_labelled_classes(problems)
    names = [t[0] for t in result]
    assert names == sorted(names), (
        "Tie-break ascending by name; got " + repr(names)
    )
    assert result[0][0] == "alpha", (
        "alpha < zebra -> alpha first in tie; got " + repr(result[0])
    )


def test_zero_coverage_before_partial() -> None:
    """0.0-coverage classes appear before partial-coverage ones.

    Verifies that 0.0 < any positive fraction in sort order.
    """
    problems = [
        _p("no_labels", 0),
        _p("no_labels", 1),
        _ps("partial", 0, "HIGH"),
        _p("partial", 1),
    ]
    result = worst_labelled_classes(problems)
    assert result[0][0] == "no_labels", (
        "0.0 coverage -> first; got " + repr(result)
    )
    assert result[1][0] == "partial", (
        "0.5 coverage -> second; got " + repr(result)
    )


def test_empty_input_returns_empty_list() -> None:
    """Empty input -> [].

    Kills impl raising on empty.
    """
    result = worst_labelled_classes([])
    assert result == [], "Empty -> []; got " + repr(result)


def test_return_type_is_list_of_two_tuples() -> None:
    """Return type is list[tuple[str, float]] — two-element tuples.

    Kills impl returning dict or three-element tuples.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = worst_labelled_classes(problems)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    for pair in result:
        assert isinstance(pair, tuple) and len(pair) == 2, (
            "Each element must be a 2-tuple; got " + repr(pair)
        )
        cls, frac = pair
        assert isinstance(cls, str) and isinstance(frac, float), (
            "Tuple must be (str, float); got " + repr((type(cls), type(frac)))
        )
