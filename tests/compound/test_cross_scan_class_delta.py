"""Item 301: cross_scan_class_delta() — per-class total problem count delta (2026-06-08).

``cross_scan_class_delta(scan_a, scan_b) -> dict[str, int]``:
Returns {class: count_b - count_a} for EVERY class in either scan.
New class (scan_b only) -> positive delta.  Disappeared class -> negative delta.
Unchanged class -> 0 in result.  Empty both -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: delta = count_b - count_a (positive = more in b; negative = fewer in b).
     Kills impl using count_a - count_b (flipped sign).
  2. New class (only in scan_b) has positive delta equal to count_b.
     Kills impl omitting classes absent from scan_a.
  3. Disappeared class (only in scan_a) has negative delta equal to -count_a.
     Kills impl omitting classes absent from scan_b.
  4. Unchanged class appears in result with delta=0 (not omitted).
     Kills impl filtering zeros out.
  5. Return type is dict[str, int].
     Kills impl returning frozenset or list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    cross_scan_class_delta,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_delta_is_count_b_minus_count_a() -> None:
    """Delta = count_b - count_a (positive means MORE in scan_b).

    PRIMARY DISCRIMINATOR: kills impl using count_a - count_b.
    alpha: scan_a=1, scan_b=3 -> delta=+2.
    beta: scan_a=3, scan_b=1 -> delta=-2.
    """
    scan_a = [_p("alpha", 0), _p("beta", 0), _p("beta", 1), _p("beta", 2)]
    scan_b = [_p("alpha", 0), _p("alpha", 1), _p("alpha", 2), _p("beta", 0)]
    result = cross_scan_class_delta(scan_a, scan_b)
    assert result["alpha"] == 2, "alpha: 3-1=+2; got " + repr(result.get("alpha"))
    assert result["beta"] == -2, "beta: 1-3=-2; got " + repr(result.get("beta"))


def test_new_class_has_positive_delta() -> None:
    """New class (only in scan_b) has delta = count_b > 0.

    Kills impl omitting classes absent from scan_a.
    'new_class' only in scan_b with 2 problems -> delta=+2.
    """
    scan_a = [_p("existing", 0)]
    scan_b = [_p("existing", 0), _p("new_class", 0), _p("new_class", 1)]
    result = cross_scan_class_delta(scan_a, scan_b)
    assert "new_class" in result, "'new_class' only in scan_b -> in result; got keys " + repr(
        list(result.keys())
    )
    assert result["new_class"] == 2, "'new_class' count_b=2, count_a=0 -> delta=+2; got " + repr(
        result["new_class"]
    )


def test_disappeared_class_has_negative_delta() -> None:
    """Disappeared class (only in scan_a) has delta = -count_a < 0.

    Kills impl omitting classes absent from scan_b.
    'gone' only in scan_a with 3 problems -> delta=-3.
    """
    scan_a = [_p("gone", 0), _p("gone", 1), _p("gone", 2), _p("existing", 0)]
    scan_b = [_p("existing", 0)]
    result = cross_scan_class_delta(scan_a, scan_b)
    assert "gone" in result, "'gone' only in scan_a -> in result; got keys " + repr(
        list(result.keys())
    )
    assert result["gone"] == -3, "'gone' count_b=0, count_a=3 -> delta=-3; got " + repr(
        result["gone"]
    )


def test_unchanged_class_has_zero_delta_in_result() -> None:
    """Unchanged class has delta=0 and IS present in result (not omitted).

    Kills impl filtering out zero-delta classes.
    """
    scan_a = [_p("stable", 0), _p("stable", 1)]
    scan_b = [_p("stable", 0), _p("stable", 1)]
    result = cross_scan_class_delta(scan_a, scan_b)
    assert "stable" in result, "'stable' class unchanged -> in result with delta=0; got " + repr(
        result
    )
    assert result["stable"] == 0, "Unchanged: delta=0; got " + repr(result["stable"])


def test_return_type_is_dict_of_int() -> None:
    """Return type is dict[str, int].

    Kills impl returning frozenset or list.
    """
    scan_a = [_p("alpha", 0)]
    scan_b = [_p("alpha", 0), _p("alpha", 1)]
    result = cross_scan_class_delta(scan_a, scan_b)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for cls, delta in result.items():
        assert isinstance(delta, int), "Values must be int; got " + repr((cls, delta, type(delta)))
