"""Item 518: bottom_fid_by_score() -- the single lowest-scoring finding ID (2026-06-08).

``bottom_fid_by_score(problems, weights) -> str | None``:
Returns the finding_id with the LOWEST total weighted severity score.
Alphabetical tie-break.  None for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the LOWEST-scoring fid (not highest).
     Kills impl reusing top_fid_by_score directly.
  2. None for empty (not raise, not "").
     Kills impl calling min([]) without guard.
  3. Alphabetical tie-break: tied bottom fids -> alphabetically first.
     Kills impl returning arbitrary/last-seen tied fid.
  4. Returns str not list.
     Kills impl returning fids_by_total_score[-1] (would be a str element
     but the test confirms the scalar, not list, contract).
  5. Accumulates multi-record fid scores correctly.
     Kills impl scoring only one record per fid.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    bottom_fid_by_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_lowest_not_highest() -> None:
    """PRIMARY DISC.: returns LOWEST-scoring fid, not highest.

    fid_high=5.0, fid_low=1.0 -> bottom is fid_low.
    Kills impl reusing top_fid_by_score.
    """
    problems = [
        _p("ClassA", "fid_high", "HIGH"),  # 5.0
        _p("ClassA", "fid_low", "LOW"),  # 1.0
    ]
    result = bottom_fid_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "fid_low", "fid_low has lowest score (1.0); got " + repr(result)
    assert result != "fid_high", "Must not return highest-scoring fid"


def test_none_for_empty_input() -> None:
    """Empty input -> None (not raise, not "").

    Kills impl calling min() without an empty guard.
    """
    result = bottom_fid_by_score([], {"HIGH": 3.0})
    assert result is None, "Empty -> None; got " + repr(result)


def test_alphabetical_tie_break_for_bottom() -> None:
    """Tied bottom fids -> alphabetically first.

    fid_beta=1.0, fid_alpha=1.0 both tied at bottom -> fid_alpha (alphabetical).
    Kills impl returning fid_beta.
    """
    problems = [
        _p("ClassA", "fid_beta", "LOW"),  # 1.0 tied
        _p("ClassA", "fid_alpha", "LOW"),  # 1.0 tied
    ]
    result = bottom_fid_by_score(problems, {"LOW": 1.0})
    assert result == "fid_alpha", "Tie -> alphabetical: fid_alpha before fid_beta; got " + repr(
        result
    )


def test_returns_str_not_list() -> None:
    """Returns str, not list.

    Ensures the function signature returns a scalar, not a list.
    """
    problems = [_p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "LOW")]
    result = bottom_fid_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert not isinstance(result, list), "Must not be a list; got " + repr(result)
    assert isinstance(result, str), "Must be str; got " + repr(type(result))


def test_multi_record_fid_accumulation_bottom() -> None:
    """Multi-record fid score accumulates; accumulated fid can still be bottom.

    fid_a: LOW(1.0)+LOW(1.0)=2.0; fid_b: HIGH(5.0)=5.0; fid_c: LOW(1.0)=1.0.
    Bottom = fid_c (1.0).
    Kills impl scoring only one record per fid.
    """
    problems = [
        _p("ClassA", "fid_a", "LOW"),
        _p("ClassA", "fid_a", "LOW"),  # fid_a total = 2.0
        _p("ClassB", "fid_b", "HIGH"),  # fid_b total = 5.0
        _p("ClassC", "fid_c", "LOW"),  # fid_c total = 1.0
    ]
    result = bottom_fid_by_score(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == "fid_c", "fid_c has lowest (1.0); got " + repr(result)
