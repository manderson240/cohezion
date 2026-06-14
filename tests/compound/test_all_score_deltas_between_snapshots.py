"""Item 492: all_score_deltas_between_snapshots() -- bulk per-class score deltas (2026-06-08).

``all_score_deltas_between_snapshots(before, after, weights) -> dict[str, float]``:
Returns {cls: score_after[cls] - score_before[cls]} for every class in the
UNION of before and after.  New classes (after only) have positive delta equal
to their after score.  Resolved classes (before only) have negative delta equal
to their before score negated.  Empty both -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: covers UNION of classes (not intersection).
     ClassA in both, ClassB only in before, ClassC only in after.
     All three classes appear in result.
     Kills impl that only returns classes present in both (intersection).
  2. Signed deltas: worsening class has positive delta; improving class negative.
     Kills impl returning abs values.
  3. New class in after only -> full positive score (before=0).
     Kills impl treating absent-in-before as 0 for before but raising.
  4. Resolved class in before only -> full negative (after=0 - before score).
     Kills impl treating absent-in-after as missing key (KeyError).
  5. Empty both -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    all_score_deltas_between_snapshots,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_covers_union_of_classes_not_intersection() -> None:
    """PRIMARY DISC.: returns deltas for UNION of before+after classes.

    ClassA in both, ClassB only in before, ClassC only in after.
    All three must appear in result.
    Kills impl returning only intersection (classes in both).
    """
    before = [_p("ClassA", "f1", "HIGH"), _p("ClassB", "f2", "HIGH")]
    after = [_p("ClassA", "f3", "HIGH"), _p("ClassA", "f4", "LOW"), _p("ClassC", "f5", "HIGH")]
    result = all_score_deltas_between_snapshots(before, after, WEIGHTS)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "ClassA" in result, "ClassA (in both) must be present"
    assert "ClassB" in result, "ClassB (before only) must be present"
    assert "ClassC" in result, "ClassC (after only) must be present"


def test_signed_deltas_worsening_positive_improving_negative() -> None:
    """Worsening class has positive delta; improving class has negative delta."""
    before = [_p("Worse", "f1", "LOW"), _p("Better", "f2", "HIGH"), _p("Better", "f3", "HIGH")]
    after = [_p("Worse", "f4", "HIGH"), _p("Worse", "f5", "HIGH"), _p("Better", "f6", "LOW")]
    result = all_score_deltas_between_snapshots(before, after, WEIGHTS)
    # Worse: before=1.0, after=6.0 -> delta=+5.0
    assert abs(result["Worse"] - 5.0) < 1e-9, "Worse delta=+5.0; got " + repr(result["Worse"])
    # Better: before=6.0, after=1.0 -> delta=-5.0
    assert abs(result["Better"] - (-5.0)) < 1e-9, "Better delta=-5.0; got " + repr(result["Better"])


def test_new_class_in_after_only_has_positive_delta() -> None:
    """New class (absent in before) contributes its full after score as positive delta."""
    before = [_p("OldClass", "f1", "HIGH")]
    after = [
        _p("OldClass", "f1", "HIGH"),
        _p("NewClass", "f2", "HIGH"),
        _p("NewClass", "f3", "LOW"),
    ]
    result = all_score_deltas_between_snapshots(before, after, WEIGHTS)
    # NewClass: before=0.0, after=4.0 -> delta=+4.0
    assert abs(result["NewClass"] - 4.0) < 1e-9, "NewClass delta=+4.0; got " + repr(result)


def test_resolved_class_in_before_only_has_negative_delta() -> None:
    """Resolved class (absent in after) has negative delta equal to its before score."""
    before = [_p("Fixed", "f1", "HIGH"), _p("Fixed", "f2", "HIGH"), _p("Remaining", "f3", "LOW")]
    after = [_p("Remaining", "f3", "LOW")]
    result = all_score_deltas_between_snapshots(before, after, WEIGHTS)
    # Fixed: before=6.0, after=0.0 -> delta=-6.0
    assert abs(result["Fixed"] - (-6.0)) < 1e-9, "Fixed delta=-6.0; got " + repr(result)


def test_empty_both_returns_empty_dict() -> None:
    """Empty before + empty after -> {} (not raise)."""
    result = all_score_deltas_between_snapshots([], [], WEIGHTS)
    assert result == {}, "Empty both -> {}; got " + repr(result)
