"""Item 283: compare_severity_distributions() — cross-scan severity delta (2026-06-08).

``compare_severity_distributions(scan_a, scan_b) -> dict[str, int]``:
Returns {severity: count_b - count_a} for every labelled severity appearing in
either scan. Positive delta = more in scan_b, negative = less. Severities
appearing in only one scan use 0 for the absent one. Labelled only. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: delta is count_b MINUS count_a (not count_a minus count_b).
     scan_a: 1 HIGH, scan_b: 3 HIGH -> delta[HIGH] = +2 (positive = more in b).
     Kills impl with flipped sign (count_a - count_b).
  2. Severity in scan_b only -> positive delta (count_b - 0).
     Kills impl that omits one-sided severities.
  3. Severity in scan_a only -> negative delta (0 - count_a).
     Kills impl that omits one-sided severities.
  4. Unlabelled (severity='') excluded from output.
     Kills impl including blank-severity entries.
  5. Return type is dict[str, int].
     Kills impl returning a list or tuple.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    compare_severity_distributions,
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


def test_delta_is_count_b_minus_count_a() -> None:
    """Delta is count_b - count_a (positive = more in scan_b).

    PRIMARY DISCRIMINATOR: kills impl using count_a - count_b (flipped sign).
    scan_a: 1 HIGH; scan_b: 3 HIGH -> delta[HIGH] = 3-1 = +2.
    """
    scan_a = [_ps("alpha", 0, "HIGH")]
    scan_b = [_ps("alpha", i, "HIGH") for i in range(3)]
    result = compare_severity_distributions(scan_a, scan_b)
    assert result.get("HIGH") == 2, "count_b(3) - count_a(1) = +2; got " + repr(result.get("HIGH"))


def test_severity_only_in_scan_b_positive_delta() -> None:
    """A severity appearing only in scan_b has delta = count_b (count_a = 0).

    Kills impl omitting one-sided severities.
    """
    scan_a = [_ps("alpha", 0, "HIGH")]
    scan_b = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "CRITICAL")]
    result = compare_severity_distributions(scan_a, scan_b)
    assert result.get("CRITICAL") == 1, "CRITICAL in scan_b only -> delta=1; got " + repr(
        result.get("CRITICAL")
    )


def test_severity_only_in_scan_a_negative_delta() -> None:
    """A severity appearing only in scan_a has delta = -count_a (count_b = 0).

    Kills impl omitting one-sided severities.
    """
    scan_a = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "CRITICAL")]
    scan_b = [_ps("alpha", 0, "HIGH")]
    result = compare_severity_distributions(scan_a, scan_b)
    assert result.get("CRITICAL") == -1, "CRITICAL in scan_a only -> delta=-1; got " + repr(
        result.get("CRITICAL")
    )


def test_unlabelled_excluded() -> None:
    """Unlabelled problems (severity='') are excluded from the result dict.

    Kills impl including '' key in the result.
    """
    scan_a = [_p("alpha", 0), _ps("alpha", 1, "HIGH")]
    scan_b = [_p("alpha", 0), _ps("alpha", 1, "HIGH")]
    result = compare_severity_distributions(scan_a, scan_b)
    assert "" not in result, "'' key must not appear in result; got " + repr(result)
    assert result.get("HIGH") == 0, "HIGH unchanged -> delta=0; got " + repr(result)


def test_return_type_is_dict() -> None:
    """Return type is dict[str, int].

    Kills impl returning a list or tuple.
    """
    result = compare_severity_distributions([], [])
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    # All values must be int
    for v in result.values():
        assert isinstance(v, int), "Values must be int; got " + repr(type(v))
