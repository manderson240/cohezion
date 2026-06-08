"""Item 321: severity_coverage_ratio() — fraction of classes affected by each severity (2026-06-08).

``severity_coverage_ratio(problems) -> dict[str, float]``:
Returns {severity: class_count_at_severity / total_distinct_classes} for every
labelled severity.  Denominator = total distinct classes in the scan (including
unlabelled-only classes).  Unlabelled excluded from numerator.
Values are in [0.0, 1.0].  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: denominator = total CLASSES not total problems.
     Kills impl dividing class_count_at_severity by len(problems).
  2. Unlabelled-only class counted in denominator but not numerator.
     Kills impl ignoring classes without labelled problems.
  3. Value 1.0 when every class has ≥1 problem at that severity.
     Kills impl with off-by-one in total class count.
  4. Empty input returns {}.
     Kills impl that crashes or divides by zero.
  5. All values are floats in [0.0, 1.0].
     Kills impl returning int or out-of-range values.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_coverage_ratio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_denominator_is_total_classes_not_total_problems() -> None:
    """Denominator = total distinct classes, NOT total problems.

    PRIMARY DISCRIMINATOR: kills impl using len(problems) as denominator.
    3 classes total (alpha, beta, gamma).  HIGH appears in alpha+beta = 2 classes.
    ratio = 2/3 ≈ 0.667.  If wrong impl uses total problems (5): ratio = 2/5 = 0.4.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("alpha", 1, "HIGH"),
        _p("beta", 0, "HIGH"),
        _p("gamma", 0, "LOW"),
        _p("gamma", 1, "LOW"),
    ]
    result = severity_coverage_ratio(problems)
    expected_high = 2 / 3
    expected_low = 1 / 3
    assert abs(result.get("HIGH", -1) - expected_high) < 1e-9, (
        f"HIGH: 2 of 3 classes -> {expected_high:.4f}; got {result.get('HIGH')!r}"
    )
    assert abs(result.get("LOW", -1) - expected_low) < 1e-9, (
        f"LOW: 1 of 3 classes -> {expected_low:.4f}; got {result.get('LOW')!r}"
    )


def test_unlabelled_only_class_counted_in_denominator() -> None:
    """Class with only unlabelled problems is in denominator but NOT numerator.

    Kills impl ignoring classes that have no labelled problems.
    2 classes: alpha (labelled HIGH), beta (unlabelled only).
    Total classes = 2.  HIGH appears in 1 class.  Ratio = 1/2 = 0.5.
    If wrong impl ignores beta in denominator: ratio = 1/1 = 1.0.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("beta", 0, ""),  # beta has only unlabelled problems
        _p("beta", 1, ""),
    ]
    result = severity_coverage_ratio(problems)
    assert abs(result.get("HIGH", -1) - 0.5) < 1e-9, (
        "HIGH: 1 of 2 total classes (beta unlabelled) -> 0.5; got " + repr(result.get("HIGH"))
    )


def test_ratio_is_one_when_all_classes_have_severity() -> None:
    """Value = 1.0 when every class in scan has ≥1 problem at that severity.

    Kills impl with off-by-one in total class count.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("beta", 0, "HIGH")]
    result = severity_coverage_ratio(problems)
    assert abs(result.get("HIGH", -1) - 1.0) < 1e-9, (
        "HIGH: both classes affected -> 1.0; got " + repr(result.get("HIGH"))
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input returns {}.

    Kills impl that crashes or divides by zero.
    """
    result = severity_coverage_ratio([])
    assert result == {}, f"empty -> {{}}; got {result!r}"


def test_values_are_floats_in_unit_interval() -> None:
    """All values are floats in [0.0, 1.0].

    Kills impl returning int or out-of-range values.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("beta", 0, "LOW")]
    result = severity_coverage_ratio(problems)
    for sev, ratio in result.items():
        assert isinstance(ratio, float), f"Value for {sev!r} must be float; got {type(ratio)!r}"
        assert 0.0 <= ratio <= 1.0, f"Value for {sev!r} must be in [0,1]; got {ratio!r}"
