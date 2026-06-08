"""Item 557: fid_max_severity_weight() -- heaviest single severity weight per fid (2026-06-08).

``fid_max_severity_weight(problems, weights) -> dict[str, float]``:
Returns {fid: max weight of any single problem with that fid}.
FID-axis complement of class_max_severity_weight.
0.0 for unknown severity.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One fid appearing in two classes; max is per-fid not per-class.
     Kills impl reusing class_max_severity_weight.
  2. Returns MAX weight (not class total / not count).
     fid_a: [HIGH=8, LOW=1] -> max=8, total=9.
     Kills impl reusing fid_total_severity_score (returns 9).
  3. Different fids have independent maxima (not global max for all).
     Kills impl returning global max for every fid.
  4. 0.0 for unknown severity weight (not KeyError).
     Kills impl using weights[p.severity] directly.
  5. Empty -> {} (not raise, not {fid: 0.0}).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_max_severity_weight


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_max_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    fid_x appears in ClassA with HIGH=10 and ClassB with LOW=1.
    Per-fid max: fid_x = 10.0 (max over both occurrences regardless of class).
    Kills impl reusing class_max_severity_weight (would give ClassA=10, ClassB=1).
    """
    problems = [
        _p("ClassA", "fid_x", "HIGH"),  # fid_x gets weight 10.0
        _p("ClassB", "fid_x", "LOW"),   # fid_x also gets weight 1.0
        _p("ClassA", "fid_y", "LOW"),   # fid_y = 1.0
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = fid_max_severity_weight(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert abs(result["fid_x"] - 10.0) < 1e-9, (
        f"fid_x max=10.0 (appears in two classes); got {result['fid_x']}"
    )
    assert abs(result["fid_y"] - 1.0) < 1e-9, f"fid_y max=1.0; got {result['fid_y']}"


def test_returns_max_not_total() -> None:
    """Returns MAX weight, not total.

    fid_a: HIGH=8 + LOW=1 -> total=9, max=8.
    Kills impl reusing fid_total_severity_score (returns 9).
    """
    problems = [
        _p("A", "fid_a", "HIGH"),  # fid_a gets 8.0
        _p("B", "fid_a", "LOW"),   # fid_a gets 1.0 -- max=8, total=9
    ]
    weights = {"HIGH": 8.0, "LOW": 1.0}
    result = fid_max_severity_weight(problems, weights)
    assert abs(result["fid_a"] - 8.0) < 1e-9, (
        f"fid_a max=8.0, total=9.0; got {result['fid_a']} (9.0 = total is wrong)"
    )


def test_different_fids_have_independent_maxima() -> None:
    """Each fid's max is independent (not the global max).

    fid_hi: HIGH=7.0 only; fid_lo: LOW=2.0 only.
    fid_lo max must be 2.0, not 7.0 (the global max).
    Kills impl returning the global max for all fids.
    """
    problems = [
        _p("A", "fid_hi", "HIGH"),  # fid_hi max = 7.0
        _p("B", "fid_lo", "LOW"),   # fid_lo max = 2.0 (NOT 7.0 = global max)
    ]
    weights = {"HIGH": 7.0, "LOW": 2.0}
    result = fid_max_severity_weight(problems, weights)
    assert abs(result["fid_hi"] - 7.0) < 1e-9, f"fid_hi max=7.0; got {result['fid_hi']}"
    assert abs(result["fid_lo"] - 2.0) < 1e-9, (
        f"fid_lo max=2.0; got {result['fid_lo']} (7.0 = global max is wrong)"
    )


def test_unknown_severity_defaults_to_zero() -> None:
    """Unknown severity label -> 0.0 (not KeyError).

    Kills impl using weights[p.severity] directly without .get().
    """
    problems = [
        _p("A", "fid_a", "GHOST"),  # not in weights -> 0.0
        _p("A", "fid_a", "MED"),    # 4.0 -> fid_a max = 4.0
    ]
    weights = {"MED": 4.0}
    result = fid_max_severity_weight(problems, weights)
    assert abs(result["fid_a"] - 4.0) < 1e-9, (
        f"fid_a max=4.0 (GHOST=0.0); got {result['fid_a']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise, not {fid: 0.0})."""
    result = fid_max_severity_weight([], {"HIGH": 5.0})
    assert result == {}, f"Empty -> {{}}; got {result}"
