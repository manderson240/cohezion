"""Item 652: fid_severity_spread() -- distinct severity count per fid.

FID-axis complement of class_severity_spread (item 651).
For each fid, count of distinct severity strings present.
int >= 1.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid NOT class; counts DISTINCT severities.
     fid 'f1': CRIT×2, HIGH×1, LOW×1 -> spread=3 (not 4 total, not keyed by class).
     Kills class-axis impl and total-count impl.
  2. Single problem -> 1.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Returns int (not float).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_severity_spread,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_distinct_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid; counts distinct severities not total.

    fid 'f1': CRITICAL×2, HIGH×1, LOW×1 -> 3 distinct (not 4 total).
    class-axis would key on 'A'; kills either wrong impl.
    """
    problems = [
        _p("A", "f1", "CRITICAL"),
        _p("A", "f1", "CRITICAL"),
        _p("A", "f1", "HIGH"),
        _p("B", "f1", "LOW"),
    ]
    result = fid_severity_spread(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 3, (
        f"CRIT×2+HIGH+LOW -> 3 distinct (not 4 total); got {result['f1']}"
    )
    assert isinstance(result["f1"], int), f"Must be int; got {type(result['f1']).__name__}"


def test_single_problem_returns_one() -> None:
    """Single problem -> 1 distinct severity."""
    problems = [_p("A", "f2", "HIGH")]
    result = fid_severity_spread(problems)
    assert result["f2"] == 1, f"Single problem -> 1; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_spread([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids each counted independently.

    fid 'f3': HIGH, HIGH, LOW -> 2 distinct.
    fid 'f4': CRITICAL, HIGH, MEDIUM, LOW -> 4 distinct.
    """
    problems = [
        _p("A", "f3", "HIGH"),
        _p("B", "f3", "HIGH"),
        _p("C", "f3", "LOW"),
        _p("A", "f4", "CRITICAL"),
        _p("B", "f4", "HIGH"),
        _p("C", "f4", "MEDIUM"),
        _p("D", "f4", "LOW"),
    ]
    result = fid_severity_spread(problems)
    assert result["f3"] == 2, f"f3: HIGH+LOW -> 2; got {result['f3']}"
    assert result["f4"] == 4, f"f4: CRIT+HIGH+MED+LOW -> 4; got {result['f4']}"


def test_returns_int() -> None:
    """Return type must be int."""
    problems = [_p("A", "f5", "HIGH")] * 5 + [_p("B", "f5", "LOW")] * 3
    result = fid_severity_spread(problems)
    assert isinstance(result["f5"], int), f"Must be int; got {type(result['f5']).__name__}"
    assert result["f5"] == 2, f"HIGH+LOW -> 2 distinct; got {result['f5']}"
