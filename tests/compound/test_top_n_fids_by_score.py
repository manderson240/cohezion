"""Item 487: top_n_fids_by_score() -- top-N fids ranked by weighted severity score (2026-06-08).

``top_n_fids_by_score(problems, weights, n) -> list[str]``:
Returns the N finding_id strings with the highest total severity score
(descending), tie-broken alphabetically (ascending).
n=0 or empty -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of FID names (not class names).
     fid1/fid2 vs ClassA/ClassB -- kills impl reusing top_n_classes_by_score.
  2. Sorted descending by score (highest fid first).
     Kills impl returning ascending or unsorted list.
  3. Alphabetical tie-break: equal scores -> alpha-first fid wins.
     Kills impl with non-deterministic tie resolution.
  4. n=0 -> [].
     Kills impl without n-guard.
  5. n > len(fids) -> all fids, no padding.
     Kills impl that pads or raises when n > len(fids).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_fids_by_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_names_not_class_names() -> None:
    """PRIMARY DISC.: returns list of fid names keyed by finding_id, not problem_class.

    fid_alpha has 2xHIGH (6.0); fid_beta has 1xHIGH (3.0).
    top_n_fids_by_score(problems, weights, 2) -> ['fid_alpha', 'fid_beta'].
    Kills impl reusing top_n_classes_by_score (which returns class names).
    """
    problems = [
        _p("ClassA", "fid_alpha", "HIGH"),
        _p("ClassB", "fid_alpha", "HIGH"),
        _p("ClassA", "fid_beta", "HIGH"),
    ]
    weights = {"HIGH": 3.0}
    result = top_n_fids_by_score(problems, weights, 2)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert all(isinstance(x, str) for x in result), "All items must be str"
    assert result == ["fid_alpha", "fid_beta"], (
        "fid_alpha highest (6.0), fid_beta second (3.0); got " + repr(result)
    )


def test_sorted_descending_by_score() -> None:
    """Highest score first (descending order).

    fid_z=5.0, fid_a=3.0, fid_m=1.0 -> ['fid_z', 'fid_a', 'fid_m'].
    Kills impl returning ascending or unsorted.
    """
    problems = [
        _p("C", "fid_a", "MED"),
        _p("C", "fid_z", "HIGH"),
        _p("C", "fid_m", "LOW"),
    ]
    result = top_n_fids_by_score(
        problems, {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}, n=3
    )
    assert result == ["fid_z", "fid_a", "fid_m"], (
        "Descending by score; got " + repr(result)
    )


def test_alphabetical_tie_break() -> None:
    """Equal scores -> alphabetically first fid comes first.

    fid_b and fid_a both score 3.0 -> fid_a before fid_b.
    Kills impl with arbitrary tie-break.
    """
    problems = [
        _p("C", "fid_b", "HIGH"),
        _p("C", "fid_a", "HIGH"),
    ]
    result = top_n_fids_by_score(problems, {"HIGH": 3.0}, n=2)
    assert result == ["fid_a", "fid_b"], (
        "Tie -> alpha asc: fid_a before fid_b; got " + repr(result)
    )


def test_n_zero_returns_empty_list() -> None:
    """n=0 -> [] (not raise)."""
    problems = [_p("C", "fid_a", "HIGH")]
    result = top_n_fids_by_score(problems, {"HIGH": 3.0}, n=0)
    assert result == [], "n=0 -> []; got " + repr(result)


def test_n_larger_than_fids_returns_all_no_padding() -> None:
    """n > number of fids -> return all fids (no padding, no raise)."""
    problems = [_p("C", "fid_a", "HIGH"), _p("C", "fid_b", "LOW")]
    result = top_n_fids_by_score(problems, {"HIGH": 3.0, "LOW": 1.0}, n=10)
    assert len(result) == 2, "Only 2 fids exist; got " + repr(result)
    assert set(result) == {"fid_a", "fid_b"}
