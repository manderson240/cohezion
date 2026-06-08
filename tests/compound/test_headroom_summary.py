"""Item 246: headroom_summary() — rich headroom report in one call (2026-06-08).

``headroom_summary(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, object]``:
Returns::

    {
        "compliant": list[str],   # classes with headroom > 0, sorted asc
        "exact":     list[str],   # classes with headroom == 0, sorted asc
        "violated":  list[str],   # classes with headroom < 0, sorted asc
        "worst":     str | None,  # class with most-negative headroom, or None
    }

The three lists are disjoint; their union (as a set) equals the keyset of
*thresholds*.  Lists are sorted ascending by class name.  *worst* is ``None``
when there are no violations.  Empty *thresholds* → all lists empty, worst None.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: worst is the class with the MOST-NEGATIVE headroom (not
     merely the first violated class).  Kills impl that sets worst=None when
     violations exist, or returns the lexically first violating class.
  2. compliant / exact / violated are disjoint.
     Kills impl where a class with headroom=0 is also in compliant.
  3. Lists are sorted ascending by class name.
     Kills impl that preserves dict-insertion order.
  4. worst is None when there are no violations.
     Kills impl that always returns a class name.
  5. Return type is dict with exactly four keys.
     Kills impl returning a tuple or using different key names.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    headroom_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_worst_is_class_with_most_negative_headroom() -> None:
    """worst = class with the lowest (most-negative) headroom.

    PRIMARY DISCRIMINATOR: kills impl that returns None when violations exist
    or returns the lexically first violating class instead of the worst one.
    alpha: headroom = 2-4 = -2.  beta: headroom = 2-3 = -1.  worst = alpha.
    """
    problems = [
        _p("alpha", 0), _p("alpha", 1), _p("alpha", 2), _p("alpha", 3),  # count=4
        _p("beta", 0), _p("beta", 1), _p("beta", 2),                      # count=3
    ]
    thresholds = {"alpha": 2, "beta": 2}
    result = headroom_summary(problems, thresholds)

    assert result["worst"] == "alpha", (
        "alpha has headroom -2 < beta headroom -1; worst must be alpha; got "
        + repr(result["worst"])
    )


def test_three_lists_are_disjoint() -> None:
    """compliant, exact, violated are disjoint.

    Kills impl where a headroom=0 class also appears in compliant.
    """
    problems = [
        _p("alpha", 0),                         # count=1, threshold=3 → compliant
        _p("beta", 0), _p("beta", 1),           # count=2, threshold=2 → exact
        _p("gamma", 0), _p("gamma", 1), _p("gamma", 2), _p("gamma", 3),  # count=4, threshold=3 → violated
    ]
    thresholds = {"alpha": 3, "beta": 2, "gamma": 3}
    result = headroom_summary(problems, thresholds)

    compliant = set(result["compliant"])
    exact = set(result["exact"])
    violated = set(result["violated"])

    assert len(compliant & exact) == 0, "compliant ∩ exact must be empty"
    assert len(compliant & violated) == 0, "compliant ∩ violated must be empty"
    assert len(exact & violated) == 0, "exact ∩ violated must be empty"
    assert compliant | exact | violated == frozenset(thresholds), "union must equal keyset"


def test_lists_are_sorted_ascending() -> None:
    """All three lists are sorted ascending by class name.

    Kills impl that preserves dict-insertion order.
    """
    problems = [
        _p("zeta", 0),
        _p("alpha", 0), _p("alpha", 1), _p("alpha", 2),
        _p("mu", 0), _p("mu", 1),
    ]
    # zeta: under, alpha: over, mu: exact
    thresholds = {"zeta": 5, "alpha": 2, "mu": 2}
    result = headroom_summary(problems, thresholds)

    # Each non-empty list must equal sorted(list)
    assert result["compliant"] == sorted(result["compliant"]), (
        "compliant must be sorted; got " + repr(result["compliant"])
    )
    assert result["exact"] == sorted(result["exact"]), (
        "exact must be sorted; got " + repr(result["exact"])
    )
    assert result["violated"] == sorted(result["violated"]), (
        "violated must be sorted; got " + repr(result["violated"])
    )


def test_worst_none_when_no_violations() -> None:
    """worst is None when there are no violated classes.

    Kills impl that always returns a class name.
    """
    problems = [_p("alpha", 0)]
    thresholds = {"alpha": 3}
    result = headroom_summary(problems, thresholds)

    assert result["worst"] is None, (
        "No violations → worst must be None; got " + repr(result["worst"])
    )


def test_return_type_is_dict_with_four_keys() -> None:
    """Return is a dict with exactly four keys.

    Kills impl returning a tuple or using different key names.
    """
    result = headroom_summary([], {})
    assert isinstance(result, dict), "Must return a dict; got " + repr(type(result))
    assert set(result.keys()) == {"compliant", "exact", "violated", "worst"}, (
        "Must have exactly four keys; got " + repr(set(result.keys()))
    )
    assert result["worst"] is None, "Empty thresholds → worst is None"
    for key in ("compliant", "exact", "violated"):
        assert isinstance(result[key], list), (
            f"{key} must be a list; got " + repr(type(result[key]))
        )
