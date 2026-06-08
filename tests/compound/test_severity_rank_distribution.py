"""Item 328: severity_rank_distribution() — fraction of labelled problems per severity rank (2026-06-08).

``severity_rank_distribution(problems, severity_order) -> dict[str, float]``:
For each severity with >=1 labelled problem, computes count/total_labelled_problems.
Denominator = total LABELLED problems (not total incl. unlabelled).
Values sum to 1.0 (within float precision).  Empty or all-unlabelled -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator = total LABELLED (not total incl. unlabelled).
     Kills impl using len(problems) as denominator.
  2. All labelled fractions sum to 1.0 (within float precision).
     Kills impl with inconsistent denominator.
  3. Severities not in problems are omitted (not in result).
     Kills impl pre-populating all severity_order entries.
  4. Empty or all-unlabelled input -> {}.
     Kills impl crashing on edge cases.
  5. Severity in problems but not in ordering is still included.
     Kills impl omitting out-of-order severities.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_rank_distribution,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_denominator_is_total_labelled_not_total_problems() -> None:
    """Denominator = total LABELLED problems, excluding unlabelled.

    PRIMARY DISCRIMINATOR: kills impl using len(problems) as denominator.
    4 problems: 2 HIGH, 1 LOW, 1 unlabelled. Total labelled = 3.
    HIGH = 2/3, LOW = 1/3. Wrong impl: HIGH = 2/4 = 0.5, LOW = 1/4 = 0.25.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _p("alpha", 3),           # unlabelled
    ]
    result = severity_rank_distribution(problems, ["HIGH", "LOW", "MEDIUM"])
    assert abs(result.get("HIGH", -1) - 2 / 3) < 1e-9, (
        "HIGH = 2/3 (total_labelled=3); got " + repr(result.get("HIGH"))
    )
    assert abs(result.get("LOW", -1) - 1 / 3) < 1e-9, (
        "LOW = 1/3 (total_labelled=3); got " + repr(result.get("LOW"))
    )


def test_labelled_fractions_sum_to_one() -> None:
    """All labelled severity fractions sum to 1.0.

    Kills impl with inconsistent denominator producing non-unit sum.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _ps("alpha", 3, "CRITICAL"),
    ]
    result = severity_rank_distribution(problems, ["CRITICAL", "HIGH", "LOW"])
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-9, "fractions must sum to 1.0; got " + repr(total)


def test_severity_not_in_problems_omitted_from_result() -> None:
    """Severities in ordering with zero problems are omitted.

    Kills impl pre-populating all severity_order entries with 0.0.
    MEDIUM not in problems -> 'MEDIUM' not in result.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "LOW")]
    result = severity_rank_distribution(problems, ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    assert "MEDIUM" not in result, "MEDIUM not in problems -> not in result; got " + repr(result)
    assert "CRITICAL" not in result, "CRITICAL not in problems -> not in result; got " + repr(result)
    assert "HIGH" in result and "LOW" in result, "HIGH+LOW in result; got " + repr(result)


def test_empty_and_all_unlabelled_return_empty_dict() -> None:
    """Empty or all-unlabelled input -> {}.

    Kills impl crashing on empty input.
    """
    assert severity_rank_distribution([], ["HIGH", "LOW"]) == {}, "empty -> {}"
    assert severity_rank_distribution([_p("alpha", 0)], ["HIGH"]) == {}, "all-unlabelled -> {}"


def test_severity_in_problems_but_not_in_ordering_included() -> None:
    """Severity not in severity_order but in problems is still in result.

    Kills impl omitting out-of-order severities.
    UNKNOWN not in ordering but in problems -> included in result.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "UNKNOWN")]
    result = severity_rank_distribution(problems, ["HIGH", "LOW"])
    assert "UNKNOWN" in result, "UNKNOWN in problems but not in ordering -> still in result; got " + repr(result)
    assert abs(result.get("HIGH", -1) - 0.5) < 1e-9, "HIGH = 1/2 = 0.5; got " + repr(result.get("HIGH"))
    assert abs(result.get("UNKNOWN", -1) - 0.5) < 1e-9, "UNKNOWN = 1/2 = 0.5; got " + repr(result.get("UNKNOWN"))
