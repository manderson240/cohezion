"""Item 267: labelling_coverage() — fraction of problems that have a severity label (2026-06-08).

``labelling_coverage(problems: list[Problem]) -> float``:
Returns labelled_problem_count(problems) / len(problems).
0.0 on empty input.  Result in [0.0, 1.0].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator is len(problems) (total), not labelled count.
     Kills impl doing labelled/labelled which always returns 1.0 when non-zero.
  2. 1.0 when all problems are labelled.
     Verifies the fully-covered case.
  3. 0.0 when no problems are labelled.
     Kills impl that divides by labelled count (would be 0/0 ZeroDivisionError).
  4. 0.0 on empty input (no ZeroDivisionError).
     Kills impl that raises when len(problems) == 0.
  5. Return type is float in [0.0, 1.0].
     Kills impl returning int or percentage > 1.0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    labelling_coverage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_denominator_is_total_not_labelled() -> None:
    """Denominator is len(problems) not labelled_problem_count.

    PRIMARY DISCRIMINATOR: kills impl doing labelled/labelled = 1.0 always.
    2 labelled out of 4 total = 0.5.
    If impl used labelled/labelled: 2/2 = 1.0 (wrong).
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1, "LOW"),
        _p("beta", 0),  # unlabelled
        _p("beta", 1),  # unlabelled
    ]
    result = labelling_coverage(problems)
    assert abs(result - 0.5) < 1e-9, "2/4=0.5; got " + repr(result)


def test_one_when_all_labelled() -> None:
    """Returns 1.0 when every problem has a non-empty severity.

    Verifies the fully-covered case.
    """
    problems = [_p("alpha", i, "HIGH") for i in range(3)]
    result = labelling_coverage(problems)
    assert abs(result - 1.0) < 1e-9, "All labelled -> 1.0; got " + repr(result)


def test_zero_when_none_labelled() -> None:
    """Returns 0.0 when no problem has a severity label.

    Kills impl that raises ZeroDivisionError when labelled count is 0.
    """
    problems = [_p("alpha", i) for i in range(3)]
    result = labelling_coverage(problems)
    assert result == 0.0, "None labelled -> 0.0; got " + repr(result)


def test_zero_on_empty_input() -> None:
    """Returns 0.0 on empty input (no ZeroDivisionError).

    Kills impl that raises when len(problems) == 0.
    """
    result = labelling_coverage([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)


def test_return_type_is_float_in_unit_interval() -> None:
    """Return type is float in [0.0, 1.0].

    Kills impl returning int or a percentage > 1.0.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("beta", 0)]
    result = labelling_coverage(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert 0.0 <= result <= 1.0, "Must be in [0.0, 1.0]; got " + repr(result)
    assert abs(result - 0.5) < 1e-9
