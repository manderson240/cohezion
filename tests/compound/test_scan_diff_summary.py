"""Item 305: scan_diff_summary() — aggregate statistics comparing two scans (2026-06-08).

``scan_diff_summary(scan_a, scan_b) -> dict[str, int]``:
Returns 8-key dict:
  total_a, total_b, delta_total, classes_grown, classes_stable,
  classes_shrunk, new_classes, disappeared_classes.
All values int.  Empty both -> all zeros.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: delta_total = total_b - total_a (NOT total_a - total_b).
     Kills impl computing the delta in the wrong direction.
  2. new_classes = classes in scan_b but not scan_a (brand new).
     Kills impl counting all classes with delta > 0 as "new".
  3. disappeared_classes = classes in scan_a but not scan_b.
     Kills impl counting all classes with delta < 0 as "disappeared".
  4. classes_grown / stable / shrunk partition all classes correctly.
     Kills impl double-counting or omitting stable classes.
  5. Empty both -> all-zero dict with all 8 keys present.
     Kills impl raising or returning fewer keys on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    scan_diff_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_delta_total_is_b_minus_a() -> None:
    """delta_total = total_b - total_a (positive = more problems in scan_b).

    PRIMARY DISCRIMINATOR: kills impl computing total_a - total_b.
    scan_a has 3, scan_b has 5 -> delta_total = +2.
    """
    scan_a = [_p("alpha", 0), _p("alpha", 1), _p("alpha", 2)]
    scan_b = [_p("alpha", 0), _p("alpha", 1), _p("alpha", 2), _p("alpha", 3), _p("alpha", 4)]
    result = scan_diff_summary(scan_a, scan_b)
    assert result["total_a"] == 3, "total_a=3; got " + repr(result["total_a"])
    assert result["total_b"] == 5, "total_b=5; got " + repr(result["total_b"])
    assert result["delta_total"] == 2, "delta_total=5-3=+2; got " + repr(result["delta_total"])


def test_new_classes_counts_only_absent_in_scan_a() -> None:
    """new_classes = classes in scan_b but NOT in scan_a (truly new).

    Kills impl counting all delta>0 classes as new.
    alpha: in both scans but grew -> NOT new.
    beta: only in scan_b -> new_classes = 1.
    """
    scan_a = [_p("alpha", 0)]
    scan_b = [_p("alpha", 0), _p("alpha", 1), _p("beta", 0)]
    result = scan_diff_summary(scan_a, scan_b)
    assert result["new_classes"] == 1, "only beta is new; got " + repr(result["new_classes"])
    assert result["classes_grown"] == 2, "alpha and beta both grew; got " + repr(result["classes_grown"])


def test_disappeared_classes_counts_only_absent_in_scan_b() -> None:
    """disappeared_classes = classes in scan_a but NOT in scan_b (truly gone).

    Kills impl counting all delta<0 classes as disappeared.
    gamma: in both scans but shrank -> NOT disappeared.
    delta: only in scan_a -> disappeared_classes = 1.
    """
    scan_a = [_p("gamma", 0), _p("gamma", 1), _p("delta_cls", 0)]
    scan_b = [_p("gamma", 0)]
    result = scan_diff_summary(scan_a, scan_b)
    assert result["disappeared_classes"] == 1, (
        "only delta_cls disappeared; got " + repr(result["disappeared_classes"])
    )
    assert result["classes_shrunk"] == 2, (
        "gamma and delta_cls both shrank; got " + repr(result["classes_shrunk"])
    )


def test_grown_stable_shrunk_partition_all_classes() -> None:
    """classes_grown + classes_stable + classes_shrunk == total unique classes.

    Kills impl double-counting or omitting stable classes.
    alpha grows, beta stable, gamma shrinks -> grown=1, stable=1, shrunk=1.
    """
    scan_a = [_p("alpha", 0), _p("beta", 0), _p("beta", 1), _p("gamma", 0), _p("gamma", 1)]
    scan_b = [_p("alpha", 0), _p("alpha", 1), _p("beta", 0), _p("beta", 1), _p("gamma", 0)]
    result = scan_diff_summary(scan_a, scan_b)
    assert result["classes_grown"] == 1, "alpha grew -> classes_grown=1; got " + repr(result)
    assert result["classes_stable"] == 1, "beta stable -> classes_stable=1; got " + repr(result)
    assert result["classes_shrunk"] == 1, "gamma shrank -> classes_shrunk=1; got " + repr(result)
    total = result["classes_grown"] + result["classes_stable"] + result["classes_shrunk"]
    assert total == 3, "partition covers all 3 classes; got total=" + repr(total)


def test_empty_both_returns_all_zero_dict_with_all_keys() -> None:
    """Empty both scans -> all-zero dict with all 8 keys present.

    Kills impl raising or returning fewer keys.
    """
    result = scan_diff_summary([], [])
    required_keys = {
        "total_a", "total_b", "delta_total",
        "classes_grown", "classes_stable", "classes_shrunk",
        "new_classes", "disappeared_classes",
    }
    assert required_keys <= set(result.keys()), (
        "All 8 keys must be present; missing: " + repr(required_keys - set(result.keys()))
    )
    for key in required_keys:
        assert result[key] == 0, f"{key} must be 0 for empty input; got " + repr(result[key])
