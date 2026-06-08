"""Item 573: fid_score_above_threshold() -- fids with score > threshold (2026-06-08).

``fid_score_above_threshold(problems, weights, threshold) -> list[str]``:
Returns fid names whose total weighted score strictly exceeds `threshold`.
FID-axis complement of class_score_above_threshold.
Sorted descending by score (then by fid name for ties).
Empty -> [].  All-below-threshold -> [].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class, 3 fids [10,5,1] threshold=4.0:
     class_above=['A'] (single class), fid_above=['f1','f2'] (two fid entries).
     Kills impl reusing class_score_above_threshold on wrong axis.
  2. Strict '>' not '>=' -- fid scoring exactly at threshold is excluded.
     Kills impl using >= (off-by-one on equality boundary).
  3. Empty problems -> [] (not raise).
     Kills impl without empty guard.
  4. All fids below threshold -> [] (not raise).
     Kills impl always returning something.
  5. Result sorted descending by score -- highest-scoring fid first.
     Kills impl returning unsorted or ascending result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_above_threshold


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    One class 'A', three fids [f1=10, f2=5, f3=1], threshold=4.0:
    class_above=['A'] (single class); fid_above=['f1','f2'] (two fids above threshold).
    Kills impl reusing class_score_above_threshold on wrong axis.
    """
    problems = [
        _p("A", "f1", "H10"),  # f1 total = 10.0
        _p("A", "f2", "H5"),   # f2 total = 5.0
        _p("A", "f3", "H1"),   # f3 total = 1.0
    ]
    weights = {"H10": 10.0, "H5": 5.0, "H1": 1.0}
    result = fid_score_above_threshold(problems, weights, 4.0)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert "f1" in result, f"f1 (10.0 > 4.0) must be included; got {result}"
    assert "f2" in result, f"f2 (5.0 > 4.0) must be included; got {result}"
    assert "f3" not in result, (
        f"f3 (1.0 not > 4.0) must be excluded; got {result} "
        f"(['A'] = class axis is wrong)"
    )
    assert len(result) == 2, f"Exactly 2 fids above 4.0; got {result}"


def test_strict_greater_than_not_gte() -> None:
    """Strict '>' -- fid at exactly threshold is excluded.

    fid_at score=5.0, threshold=5.0: must NOT appear.
    fid_above score=10.0, threshold=5.0: must appear.
    Kills impl using >= (would include fid_at).
    """
    problems = [
        _p("A", "fid_at", "FIVE"),    # fid_at total = 5.0
        _p("B", "fid_above", "TEN"),  # fid_above total = 10.0
    ]
    weights = {"FIVE": 5.0, "TEN": 10.0}
    result = fid_score_above_threshold(problems, weights, 5.0)
    assert "fid_above" in result, f"fid_above (10.0 > 5.0) must be included; got {result}"
    assert "fid_at" not in result, (
        f"fid_at (5.0 == threshold) must be EXCLUDED by strict >; got {result} "
        f"(found fid_at -> impl uses >= instead of >)"
    )


def test_empty_returns_empty_list() -> None:
    """Empty problems -> [] (not raise).

    Kills impl without empty guard.
    """
    result = fid_score_above_threshold([], {"HIGH": 5.0}, 0.0)
    assert result == [], f"Empty -> []; got {result}"


def test_all_below_threshold_returns_empty() -> None:
    """All fids below threshold -> [].

    Kills impl always returning something.
    """
    problems = [_p("A", "f1", "LOW"), _p("B", "f2", "LOW")]
    weights = {"LOW": 1.0}
    result = fid_score_above_threshold(problems, weights, 5.0)
    assert result == [], f"All fid scores (1.0) below threshold (5.0) -> []; got {result}"


def test_result_sorted_descending_by_score() -> None:
    """Result sorted descending by score (highest-scoring fid first).

    Kills impl returning unsorted or ascending result.
    """
    problems = [
        _p("A", "f_low", "LOW"),    # f_low total = 1.0
        _p("B", "f_high", "HIGH"),  # f_high total = 10.0
        _p("C", "f_mid", "MED"),    # f_mid total = 5.0
    ]
    weights = {"LOW": 1.0, "MED": 5.0, "HIGH": 10.0}
    result = fid_score_above_threshold(problems, weights, 0.5)
    # All three exceed 0.5; descending order: f_high(10) > f_mid(5) > f_low(1)
    assert result == ["f_high", "f_mid", "f_low"], (
        f"Descending sort: f_high(10) > f_mid(5) > f_low(1); got {result} "
        f"(ascending or unsorted order is wrong)"
    )
