"""Item 517: top_fid_by_score() -- the single highest-scoring finding ID (2026-06-08).

``top_fid_by_score(problems, weights) -> str | None``:
Returns the finding_id with the highest total weighted severity score.
Alphabetical tie-break.  None for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns a STRING fid name, not a class name.
     Kills impl reusing top_class_by_score on the wrong axis.
  2. None for empty (not raise, not "").
     Kills impl calling max([]) without guard.
  3. Alphabetical tie-break: tied top fids -> alphabetically first.
     Kills impl returning arbitrary/last-seen tied fid.
  4. Returns the HIGHEST-scoring fid (not lowest).
     Kills impl returning min instead of max.
  5. Accumulates multi-record fid scores correctly.
     Kills impl scoring only one record per fid.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_fid_by_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_not_class_name() -> None:
    """PRIMARY DISC.: returns fid name, not class name.

    fid1 → HIGH(5.0), fid2 → LOW(1.0); top fid is "fid1" not "ClassA".
    Kills impl reusing top_class_by_score on wrong axis.
    """
    problems = [
        _p("ClassA", "fid1", "HIGH"),  # fid1: 5.0
        _p("ClassA", "fid2", "LOW"),  # fid2: 1.0
    ]
    result = top_fid_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "fid1", "fid1 has highest score (5.0); got " + repr(result)
    assert result != "ClassA", "Must return fid, not class name"


def test_none_for_empty_input() -> None:
    """Empty input -> None (not raise, not "").

    Kills impl calling max() without an empty guard.
    """
    result = top_fid_by_score([], {"HIGH": 3.0})
    assert result is None, "Empty -> None; got " + repr(result)


def test_alphabetical_tie_break() -> None:
    """Tied top fids -> alphabetically first.

    fid_alpha=3.0, fid_beta=3.0 -> fid_alpha (alphabetical).
    Kills impl returning fid_beta or arbitrary choice.
    """
    problems = [
        _p("ClassA", "fid_beta", "HIGH"),  # 3.0 tied
        _p("ClassA", "fid_alpha", "HIGH"),  # 3.0 tied
    ]
    result = top_fid_by_score(problems, {"HIGH": 3.0})
    assert result == "fid_alpha", "Tie -> alphabetical: fid_alpha before fid_beta; got " + repr(
        result
    )


def test_returns_highest_not_lowest() -> None:
    """Returns the HIGHEST-scoring fid, not the lowest.

    Kills impl returning min() instead of max().
    """
    problems = [
        _p("ClassA", "low_fid", "LOW"),  # 1.0
        _p("ClassA", "high_fid", "HIGH"),  # 5.0
        _p("ClassA", "mid_fid", "MED"),  # 3.0
    ]
    result = top_fid_by_score(problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0})
    assert result == "high_fid", "Highest-scoring fid is 'high_fid'; got " + repr(result)
    assert result != "low_fid", "Must not return lowest-scoring fid"


def test_multi_record_fid_accumulation() -> None:
    """Multi-record fid score accumulates correctly; accumulated fid can win.

    fid_a: HIGH(3.0) + LOW(1.0) = 4.0; fid_b: HIGH(3.0) = 3.0 -> fid_a wins.
    Kills impl scoring only one record per fid.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),  # +3.0
        _p("ClassA", "fid_a", "LOW"),  # +1.0 -> total 4.0
        _p("ClassB", "fid_b", "HIGH"),  # 3.0
    ]
    result = top_fid_by_score(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result == "fid_a", "fid_a accumulates to 4.0 > fid_b 3.0; got " + repr(result)
