"""Item 416: top_n_finding_ids() — N finding_ids with highest total counts (2026-06-08).

``top_n_finding_ids(problems, n) -> list[tuple[str, int]]``:
Returns the N finding_ids with the highest total record counts as (fid, count) tuples,
sorted descending by count then ascending by fid for ties.
n <= 0 or empty -> [].  n > distinct fids -> all fids.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns list of (str, int) TUPLES keyed on finding_id.
     Kills impl reusing top_n_classes (operates on class histogram, not fid histogram).
  2. Sorted descending by count; ties broken alphabetically ascending by fid.
     Kills impl using insertion order or ascending sort.
  3. n <= 0 returns [] (not ValueError or all fids).
     Kills impl treating n=0 as "all".
  4. n > distinct fids returns all fids (not raise).
     Kills impl slicing blindly with IndexError.
  5. Empty input returns [].
     Kills impl raising on empty histogram.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    top_n_finding_ids,
)


def _p(fid: str, cls: str = "cls") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_fid_count_tuples_not_class_tuples() -> None:
    """Returns (fid, count) tuples based on finding_id histogram.

    PRIMARY DISCRIMINATOR: kills impl reusing top_n_classes (class histogram).
    """
    problems = [_p("fid_a"), _p("fid_a"), _p("fid_a"), _p("fid_b")]
    result = top_n_finding_ids(problems, n=1)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 1
    assert isinstance(result[0], tuple), "Each element must be tuple; got " + repr(type(result[0]))
    assert result[0] == ("fid_a", 3), "top fid is fid_a=3; got " + repr(result[0])


def test_sorted_descending_with_alphabetical_tiebreak() -> None:
    """Sorted descending by count; ties broken alphabetically ascending by fid."""
    problems = [
        _p("beta_fid"), _p("beta_fid"),
        _p("alpha_fid"), _p("alpha_fid"),
        _p("gamma_fid"),
    ]
    result = top_n_finding_ids(problems, n=3)
    assert result[0][1] == 2 and result[1][1] == 2
    # alphabetical tie-break: alpha_fid < beta_fid
    assert result[0] == ("alpha_fid", 2), "alpha before beta (tie); got " + repr(result[0])
    assert result[1] == ("beta_fid", 2)
    assert result[2] == ("gamma_fid", 1)


def test_n_zero_or_negative_returns_empty() -> None:
    """n <= 0 returns [], not all fids."""
    problems = [_p("a"), _p("b"), _p("a")]
    assert top_n_finding_ids(problems, n=0) == [], "n=0 -> []"
    assert top_n_finding_ids(problems, n=-5) == [], "n<0 -> []"


def test_n_exceeds_fid_count_returns_all() -> None:
    """n greater than distinct fid count returns all fids (no IndexError)."""
    problems = [_p("x"), _p("y"), _p("x")]
    result = top_n_finding_ids(problems, n=100)
    assert len(result) == 2, "Only 2 distinct fids; got " + repr(len(result))
    assert result[0] == ("x", 2)
    assert result[1] == ("y", 1)


def test_empty_returns_empty_list() -> None:
    """Empty input returns []."""
    assert top_n_finding_ids([], n=3) == []
