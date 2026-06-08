"""Item 571: fid_score_bottom_n() -- bottom N fids by total weighted score (2026-06-08).

``fid_score_bottom_n(problems, weights, n) -> list[str]``:
Returns the N lowest-scoring fid names sorted ascending by score.
FID-axis complement of class_score_bottom_n.
Ties broken lexicographically.  Empty -> [].  n=0 -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class, three fids [10,5,1] n=2:
     class_score_bottom_n=['A'] (single class), fid_score_bottom_n=['f3','f2'].
     Kills impl reusing class_score_bottom_n on wrong axis.
  2. Returns LOWEST scores (ascending), not highest (descending).
     [f1=10, f2=5, f3=1] n=2: bottom=['f3','f2'] not top=['f1','f2'].
     Kills impl reusing fid_score_top_n without reversal.
  3. n=0 -> [] (not raise).
     Kills impl without n=0 guard.
  4. Empty problems -> [] (not raise).
     Kills impl without empty guard.
  5. Fewer than n fids -> return all.
     Kills impl that requires exactly n fids.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_bottom_n


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    One class 'A', three fids [f1=10, f2=5, f3=1], n=2:
    class_score_bottom_n(['A']) has 1 key; fid_score_bottom_n=['f3','f2'] has 2 fid entries.
    Kills impl reusing class_score_bottom_n on wrong axis.
    """
    problems = [
        _p("A", "f1", "H10"),  # f1 total = 10.0
        _p("A", "f2", "H5"),  # f2 total = 5.0
        _p("A", "f3", "H1"),  # f3 total = 1.0
    ]
    weights = {"H10": 10.0, "H5": 5.0, "H1": 1.0}
    result = fid_score_bottom_n(problems, weights, 2)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 2, f"n=2 -> 2 names; got {result}"
    # Bottom 2 fids: f3(1.0) and f2(5.0); class_bottom_n would return ['A']
    assert "f3" in result, (
        f"f3 (lowest=1.0) must be in bottom 2; got {result} (['A'] = class axis is wrong)"
    )
    assert "f2" in result, f"f2 (middle=5.0) must be in bottom 2; got {result}"
    assert "f1" not in result, f"f1 (highest=10.0) must NOT be in bottom 2; got {result}"


def test_returns_lowest_not_highest() -> None:
    """Returns LOWEST scores (ascending), not highest (descending).

    [f1=10, f2=5, f3=1] n=2: bottom=['f3','f2'] (ascending);
    top_n would give ['f1','f2'] (descending).
    Kills impl reusing fid_score_top_n without reversal.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # f1 total = 10.0
        _p("B", "f2", "MEDIUM"),  # f2 total = 5.0
        _p("C", "f3", "LOW"),  # f3 total = 1.0
    ]
    weights = {"HIGH": 10.0, "MEDIUM": 5.0, "LOW": 1.0}
    result = fid_score_bottom_n(problems, weights, 2)
    assert result[0] == "f3", (
        f"Ascending sort: f3 (1.0) first; got {result} ('f1' first = top_n direction is wrong)"
    )
    assert result[1] == "f2", f"Second lowest: f2 (5.0); got {result}"


def test_n_zero_returns_empty() -> None:
    """n=0 -> [] (not raise).

    Kills impl without n=0 guard.
    """
    result = fid_score_bottom_n([_p("A", "f1", "HIGH")], {"HIGH": 5.0}, 0)
    assert result == [], f"n=0 -> []; got {result}"


def test_empty_returns_empty_list() -> None:
    """Empty problems -> [] (not raise).

    Kills impl without empty guard.
    """
    result = fid_score_bottom_n([], {"HIGH": 5.0}, 3)
    assert result == [], f"Empty -> []; got {result}"


def test_fewer_than_n_fids_returns_all() -> None:
    """Fewer than n fids -> return all available (not raise).

    Kills impl that requires exactly n fids or raises IndexError.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "LOW")]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = fid_score_bottom_n(problems, weights, 10)
    assert len(result) == 2, f"2 fids with n=10 -> return both; got {result}"
    # Ascending sort: f2(1.0) first, f1(5.0) second
    assert result[0] == "f2", f"Ascending: f2(1.0) first; got {result}"
    assert result[1] == "f1", f"Ascending: f1(5.0) second; got {result}"
