"""Item 304: class_stability_report() — label every class as growing/stable/shrinking (2026-06-08).

``class_stability_report(scan_a, scan_b) -> dict[str, str]``:
Returns a dict mapping each class name (from either scan) to exactly one of
"growing", "stable", or "shrinking" based on its total count delta.
Empty both scans -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: delta=0 classes get label "stable" (not omitted).
     Kills impl that filters out unchanged classes.
  2. New class (only in scan_b) gets label "growing".
     Kills impl that errors on absent-in-scan-a classes.
  3. Disappeared class (only in scan_a) gets label "shrinking".
     Kills impl that errors on absent-in-scan-b classes.
  4. All three labels correct simultaneously.
     Kills impl that confuses "growing" and "shrinking" directions.
  5. Empty both scans -> {}.
     Kills impl raising on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_stability_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_stable_class_included_with_stable_label() -> None:
    """delta=0 classes are labelled 'stable', NOT omitted.

    PRIMARY DISCRIMINATOR: kills impl that drops unchanged classes.
    alpha: 2 in scan_a, 2 in scan_b -> delta=0 -> 'stable'.
    """
    scan_a = [_p("alpha", 0), _p("alpha", 1)]
    scan_b = [_p("alpha", 0), _p("alpha", 1)]
    result = class_stability_report(scan_a, scan_b)
    assert "alpha" in result, "alpha present in both scans -> must be in report; got " + repr(
        result
    )
    assert result["alpha"] == "stable", "alpha unchanged -> 'stable'; got " + repr(result["alpha"])


def test_new_class_in_scan_b_labelled_growing() -> None:
    """Class only in scan_b (new) is labelled 'growing'.

    Kills impl raising KeyError or mishandling absent-in-scan-a.
    beta: 0 in scan_a, 2 in scan_b -> delta=+2 -> 'growing'.
    """
    scan_a = []
    scan_b = [_p("beta", 0), _p("beta", 1)]
    result = class_stability_report(scan_a, scan_b)
    assert "beta" in result, "beta new in scan_b -> in report; got " + repr(result)
    assert result["beta"] == "growing", "beta new (delta=+2) -> 'growing'; got " + repr(
        result["beta"]
    )


def test_disappeared_class_labelled_shrinking() -> None:
    """Class only in scan_a (gone) is labelled 'shrinking'.

    Kills impl raising KeyError or mishandling absent-in-scan-b.
    gamma: 3 in scan_a, 0 in scan_b -> delta=-3 -> 'shrinking'.
    """
    scan_a = [_p("gamma", 0), _p("gamma", 1), _p("gamma", 2)]
    scan_b = []
    result = class_stability_report(scan_a, scan_b)
    assert "gamma" in result, "gamma disappeared -> in report; got " + repr(result)
    assert result["gamma"] == "shrinking", "gamma gone (delta=-3) -> 'shrinking'; got " + repr(
        result["gamma"]
    )


def test_all_three_labels_correct_simultaneously() -> None:
    """All three labels co-exist correctly in one call.

    Kills impl confusing direction: growing/shrinking must not be swapped.
    alpha grows, beta stable, gamma shrinks.
    """
    scan_a = [
        _p("alpha", 0),
        _p("beta", 0),
        _p("beta", 1),
        _p("gamma", 0),
        _p("gamma", 1),
        _p("gamma", 2),
    ]
    scan_b = [
        _p("alpha", 0),
        _p("alpha", 1),  # alpha: 1->2, delta=+1
        _p("beta", 0),
        _p("beta", 1),  # beta:  2->2, delta=0
        _p("gamma", 0),  # gamma: 3->1, delta=-2
    ]
    result = class_stability_report(scan_a, scan_b)
    assert result.get("alpha") == "growing", "alpha grew -> 'growing'; got " + repr(result)
    assert result.get("beta") == "stable", "beta unchanged -> 'stable'; got " + repr(result)
    assert result.get("gamma") == "shrinking", "gamma shrank -> 'shrinking'; got " + repr(result)


def test_empty_both_scans_returns_empty_dict() -> None:
    """Empty both scans -> {}, not an exception.

    Kills impl raising on empty input.
    """
    result = class_stability_report([], [])
    assert result == {}, "Both empty -> {}; got " + repr(result)
