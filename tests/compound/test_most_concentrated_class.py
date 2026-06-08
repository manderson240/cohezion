"""Item 258: most_concentrated_class() — class with highest per-class fraction at severity (2026-06-08).

``most_concentrated_class(problems: list[Problem], severity: str) -> str | None``:
Returns the class name with the highest fraction
``count_at_severity / total_problems_in_class`` at *severity*.  Tie-break:
class name ascending alphabetically.  Returns ``None`` when no class has any
problems at *severity* or when the input is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: uses per-class fraction (at_severity / class_total), NOT
     raw count at severity.  Kills impl returning the class with the most raw
     problems at that severity (i.e. top_classes_by_severity[0]).
  2. Tie-break is alphabetically ascending class name.
     Kills impl with unstable sort or wrong tie-break direction.
  3. Returns None when no class has problems at the target severity.
     Kills impl returning the class with the most problems overall.
  4. Returns None when input is empty.
     Kills impl that raises on empty input.
  5. Return type is str | None.
     Kills impl returning a float (the fraction) or a dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_concentrated_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fraction_based_not_count_based() -> None:
    """Uses per-class fraction, not raw count, for ranking.

    PRIMARY DISCRIMINATOR: kills impl that returns the class with the most raw
    HIGH problems (count-based).
    alpha: 1 HIGH / 1 total = 1.0 (100%).
    beta:  5 HIGH / 20 total = 0.25 (25%).
    Most concentrated = alpha (1.0 > 0.25), even though beta has more HIGH problems.
    """
    problems = (
        [_ps("alpha", 0, "HIGH")]
        + [_ps("beta", i, "HIGH") for i in range(5)]
        + [_ps("beta", i + 5, "LOW") for i in range(15)]
    )
    result = most_concentrated_class(problems, "HIGH")
    assert result == "alpha", (
        "alpha 1/1=100% beats beta 5/20=25%; got " + repr(result)
    )


def test_tie_break_alphabetically_ascending() -> None:
    """When two classes have equal fraction, returns the lexicographically first.

    Kills impl with unstable sort or descending tie-break.
    alpha: 1/1=1.0, zeta: 1/1=1.0.  Tie-break → alpha < zeta.
    """
    problems = [_ps("zeta", 0, "HIGH"), _ps("alpha", 0, "HIGH")]
    result = most_concentrated_class(problems, "HIGH")
    assert result == "alpha", (
        "Tie: alpha < zeta alphabetically → alpha; got " + repr(result)
    )


def test_none_when_no_class_has_target_severity() -> None:
    """Returns None when no class has any problems at the target severity.

    Kills impl that returns the class with the most overall problems.
    """
    problems = [_ps("alpha", 0, "LOW"), _ps("beta", 0, "LOW")]
    result = most_concentrated_class(problems, "HIGH")
    assert result is None, (
        "No HIGH problems → None; got " + repr(result)
    )


def test_none_when_empty_input() -> None:
    """Returns None when problems list is empty.

    Kills impl that raises on empty input.
    """
    result = most_concentrated_class([], "HIGH")
    assert result is None, "Empty input → None; got " + repr(result)


def test_return_type_is_str_or_none() -> None:
    """Return type is str | None.

    Kills impl returning a float or a dict.
    """
    result = most_concentrated_class([_ps("alpha", 0, "HIGH")], "HIGH")
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "alpha"
