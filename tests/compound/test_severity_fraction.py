"""Item 250: severity_fraction() — fraction of labelled problems at severity (2026-06-08).

``severity_fraction(problems: list[Problem], severity: str) -> float``:
Returns the proportion of *labelled* (non-empty-severity) problems that are at
the specified severity level::

    count_at_severity / total_labelled_problems

The denominator is the count of problems with non-empty severity — unlabelled
problems (``severity=""``) are excluded from both numerator and denominator.
Returns ``0.0`` when the severity is absent or when there are no labelled
problems.  Result is in ``[0.0, 1.0]``.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator is total LABELLED problems, not len(problems).
     Kills impl that divides by len(problems) and includes unlabelled ones.
  2. Returns 0.0 when the severity is absent from the scan.
     Kills impl that raises ZeroDivisionError or KeyError.
  3. Returns 0.0 when no problem has a non-empty severity.
     Kills impl that divides by 0 when denominator is 0.
  4. Result equals count_at_severity / total_labelled.
     Kills impl that uses a set (unique classes) instead of raw count.
  5. Return type is float in [0.0, 1.0].
     Kills impl returning int or a percentage > 1.0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_fraction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_denominator_is_labelled_not_total() -> None:
    """Denominator is total labelled problems, not len(problems).

    PRIMARY DISCRIMINATOR: kills impl that divides by len(problems) which
    would include unlabelled problems (severity="") in the denominator.
    2 HIGH labelled, 1 unlabelled.  labelled=2, HIGH=2. fraction = 2/2 = 1.0.
    If denominator were len(problems)=3: fraction would be 2/3 ≈ 0.667.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        Problem(problem_class="beta", finding_id="beta:0"),  # severity=""
    ]
    result = severity_fraction(problems, "HIGH")
    assert abs(result - 1.0) < 1e-9, (
        "2 HIGH out of 2 labelled = 1.0; got " + repr(result)
    )


def test_absent_severity_returns_zero() -> None:
    """Returns 0.0 when the severity level has no problems.

    Kills impl that raises KeyError on missing severity.
    """
    problems = [_ps("alpha", 0, "LOW")]
    result = severity_fraction(problems, "HIGH")
    assert result == 0.0, "HIGH absent → 0.0; got " + repr(result)


def test_no_labelled_problems_returns_zero() -> None:
    """Returns 0.0 when no problem has a non-empty severity.

    Kills impl that raises ZeroDivisionError.
    """
    problems = [
        Problem(problem_class="alpha", finding_id="alpha:0"),
        Problem(problem_class="beta", finding_id="beta:0"),
    ]
    result = severity_fraction(problems, "HIGH")
    assert result == 0.0, "No labelled problems → 0.0; got " + repr(result)


def test_fraction_uses_raw_count_not_set_size() -> None:
    """Result equals count_at_severity / total_labelled (raw counts).

    Kills impl that uses unique class names as the count.
    3 HIGH (two from alpha, one from beta), 1 LOW.  total_labelled=4.
    fraction = 3/4 = 0.75.
    """
    problems = [
        _ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH"),
        _ps("beta",  0, "HIGH"),
        _ps("gamma", 0, "LOW"),
    ]
    result = severity_fraction(problems, "HIGH")
    assert abs(result - 0.75) < 1e-9, "3 HIGH / 4 labelled = 0.75; got " + repr(result)


def test_return_type_is_float_in_unit_interval() -> None:
    """Return type is float in [0.0, 1.0].

    Kills impl returning int or percentage > 1.0.
    """
    problems = [_ps("alpha", 0, "CRITICAL")]
    result = severity_fraction(problems, "CRITICAL")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert 0.0 <= result <= 1.0, "Must be in [0.0, 1.0]; got " + repr(result)
    assert result == 1.0, "Only CRITICAL → 1.0; got " + repr(result)
