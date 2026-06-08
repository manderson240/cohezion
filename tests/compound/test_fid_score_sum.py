"""Item 542: fid_score_sum() -- total weighted score across all fids (2026-06-08).

``fid_score_sum(problems, weights) -> float``:
Returns the sum of all per-fid total weighted scores.
Equals the sum of individual problem weights (fid aggregation is transparent).
0.0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns weighted SUM (not problem count).
     Kills impl returning len(problems) for different-weight severities.
  2. Equal to sum of individual problem weights (fid aggregation is transparent).
     Kills impl that double-counts or under-counts due to aggregation error.
  3. 0.0 for empty (not raise).
     Kills impl without empty guard.
  4. Unknown severity contributes 0.0 (weight defaults to 0).
     Kills impl that raises on missing severity key.
  5. Single fid accumulates multiple problems correctly.
     Kills impl that counts fids instead of summing their totals.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_sum


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_weighted_sum_not_count() -> None:
    """PRIMARY DISC.: returns weighted sum, not problem count.

    3 problems: 2x HIGH(5.0) on fid_a + 1x LOW(1.0) on fid_b = sum 11.0; count = 3.
    Kills impl returning len(problems) (would return 3, not 11.0).
    """
    problems = [
        _p("A", "fid_a", "HIGH"),  # fid_a += 5.0
        _p("B", "fid_a", "HIGH"),  # fid_a += 5.0 -> total 10.0
        _p("C", "fid_b", "LOW"),  # fid_b total = 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = fid_score_sum(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # weighted sum = 10+1 = 11.0; problem count = 3 -- must not be 3.0
    assert abs(result - 11.0) < 1e-9, (
        f"Weighted fid sum [fid_a=10, fid_b=1] = 11.0; got {result} (3.0 = count is wrong)"
    )


def test_sum_equals_individual_weights_sum() -> None:
    """Fid aggregation is transparent: sum(fid_totals) == sum(all weights).

    fid_a: 2x HIGH(10.0) -> 20.0; fid_b: 1x MED(3.0) -> 3.0; fid_c: 2x LOW(1.0) -> 2.0.
    fid_score_sum = 25.0; direct sum of weights = 10+10+3+1+1 = 25.0.
    """
    problems = [
        _p("A", "fid_a", "HIGH"),  # +10.0
        _p("B", "fid_a", "HIGH"),  # +10.0 -> fid_a = 20.0
        _p("C", "fid_b", "MED"),  # fid_b = 3.0
        _p("D", "fid_c", "LOW"),  # +1.0
        _p("E", "fid_c", "LOW"),  # +1.0 -> fid_c = 2.0
    ]
    weights = {"HIGH": 10.0, "MED": 3.0, "LOW": 1.0}
    result = fid_score_sum(problems, weights)
    assert abs(result - 25.0) < 1e-9, f"Sum of fid totals [20,3,2] = 25.0; got {result}"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = fid_score_sum([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_unknown_severity_contributes_zero() -> None:
    """Problem with unknown severity contributes 0.0 to the sum.

    Kills impl that raises KeyError for missing severity key.
    """
    problems = [
        _p("A", "fid_known", "KNOWN"),  # +5.0
        _p("B", "fid_unk", "UNKNOWN"),  # +0.0 (not in weights)
    ]
    weights = {"KNOWN": 5.0}
    result = fid_score_sum(problems, weights)
    assert abs(result - 5.0) < 1e-9, f"KNOWN(5.0) + UNKNOWN(0.0) = 5.0; got {result}"


def test_single_fid_accumulates_correctly() -> None:
    """Single fid with multiple problems: sum their contributions.

    Kills impl that counts distinct fids instead of summing their totals.
    """
    problems = [
        _p("A", "only_fid", "HIGH"),  # +10.0
        _p("B", "only_fid", "HIGH"),  # +10.0
        _p("C", "only_fid", "LOW"),  # +1.0  -> only_fid total = 21.0
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = fid_score_sum(problems, weights)
    # sum of fid totals = 21.0 (single fid, total 21.0)
    # wrong impl counting fids = 1.0
    assert abs(result - 21.0) < 1e-9, (
        f"Single fid total 21.0 -> fid_score_sum = 21.0; got {result} (1.0 = fid count is wrong)"
    )
