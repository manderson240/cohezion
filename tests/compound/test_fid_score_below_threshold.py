"""Item 575: fid_score_below_threshold() -- fids with score < threshold (2026-06-08).

``fid_score_below_threshold(problems, weights, threshold) -> list[str]``:
Returns fid names whose total weighted score is strictly below `threshold`.
FID-axis complement of class_score_below_threshold.
Sorted ascending by score (then by fid name for ties).
Empty -> [].  All-above-threshold -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class 'A', three fids [f1=10, f2=5, f3=1], threshold=6.0:
     class_below=['A'] is wrong (A's class total=16 is not < 6);
     fid_below=['f2','f3'] (two fids below 6.0).
     Kills impl reusing class_score_below_threshold on wrong axis.
  2. Strict '<' not '<=' -- fid at exactly threshold is excluded.
     Kills impl using <= (includes boundary fid).
  3. Empty problems -> [] (not raise).
     Kills impl without empty guard.
  4. All fids above threshold -> [].
     Kills impl always returning something.
  5. Result sorted ascending by score -- lowest-scoring fid first.
     Kills impl returning descending result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_below_threshold


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    One class 'A', three fids [f1=10, f2=5, f3=1], threshold=6.0:
    fid_below=['f2','f3'] (fids with score < 6.0).
    class_score_below_threshold(['A'] when A total < 6, but A total=16 here -- different axis).
    Kills impl reusing class_score_below_threshold on wrong axis.
    """
    problems = [
        _p("A", "f1", "H10"),  # f1 total = 10.0
        _p("A", "f2", "H5"),  # f2 total = 5.0
        _p("A", "f3", "H1"),  # f3 total = 1.0
    ]
    weights = {"H10": 10.0, "H5": 5.0, "H1": 1.0}
    result = fid_score_below_threshold(problems, weights, 6.0)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert "f2" in result, f"f2 (5.0 < 6.0) must be included; got {result}"
    assert "f3" in result, f"f3 (1.0 < 6.0) must be included; got {result}"
    assert "f1" not in result, (
        f"f1 (10.0 not < 6.0) must be excluded; got {result} (class axis would give wrong result)"
    )
    assert len(result) == 2, f"Exactly 2 fids below 6.0; got {result}"


def test_strict_less_than_not_lte() -> None:
    """Strict '<' -- fid at exactly threshold is excluded.

    fid_at score=5.0, threshold=5.0: must NOT appear.
    fid_below score=1.0, threshold=5.0: must appear.
    Kills impl using <= (would include fid_at).
    """
    problems = [
        _p("A", "fid_at", "FIVE"),  # fid_at total = 5.0
        _p("B", "fid_below", "ONE"),  # fid_below total = 1.0
    ]
    weights = {"FIVE": 5.0, "ONE": 1.0}
    result = fid_score_below_threshold(problems, weights, 5.0)
    assert "fid_below" in result, f"fid_below (1.0 < 5.0) must be included; got {result}"
    assert "fid_at" not in result, (
        f"fid_at (5.0 == threshold) must be EXCLUDED by strict <; got {result} "
        f"(found fid_at -> impl uses <= instead of <)"
    )


def test_empty_returns_empty_list() -> None:
    """Empty problems -> [] (not raise).

    Kills impl without empty guard.
    """
    result = fid_score_below_threshold([], {"HIGH": 5.0}, 10.0)
    assert result == [], f"Empty -> []; got {result}"


def test_all_above_threshold_returns_empty() -> None:
    """All fids above threshold -> [].

    Kills impl always returning something.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "HIGH")]
    weights = {"HIGH": 10.0}
    result = fid_score_below_threshold(problems, weights, 5.0)
    assert result == [], f"All fid scores (10.0) above threshold (5.0) -> []; got {result}"


def test_result_sorted_ascending_by_score() -> None:
    """Result sorted ascending by score (lowest-scoring fid first).

    Kills impl returning descending or unsorted result.
    """
    problems = [
        _p("A", "f_lo", "LOW"),  # f_lo total = 1.0
        _p("B", "f_hi", "HIGH"),  # f_hi total = 10.0
        _p("C", "f_mid", "MED"),  # f_mid total = 5.0
    ]
    weights = {"LOW": 1.0, "MED": 5.0, "HIGH": 10.0}
    # threshold=15.0 -> all three qualify (all < 15.0); ascending: f_lo(1) < f_mid(5) < f_hi(10)
    result = fid_score_below_threshold(problems, weights, 15.0)
    assert result == ["f_lo", "f_mid", "f_hi"], (
        f"Ascending sort: f_lo(1) < f_mid(5) < f_hi(10); got {result} "
        f"(descending or unsorted is wrong)"
    )
