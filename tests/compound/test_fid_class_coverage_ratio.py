"""Item 620: fid_class_coverage_ratio() -- fraction of total classes covered per fid.

FID-axis complement of class_fid_coverage_ratio (item 619).
Returns {fid: distinct_classes_for_fid / total_distinct_classes}.
float in (0.0, 1.0].  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_class_coverage_ratio


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_ratio_uses_total_classes_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid; denominator = TOTAL distinct classes.

    4 total distinct classes. fid 'f1' appears in 2 of them.
    result['f1'] == 0.5 (not 2=absolute count, not result['A']=wrong axis).
    Kills impl returning absolute class count or using wrong axis.
    """
    problems = [_p("A", "f1"), _p("B", "f1"), _p("C", "f2"), _p("D", "f2")]
    result = fid_class_coverage_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 0.5) < 1e-9, (
        f"f1 in 2 of 4 classes -> 0.5; got {result['f1']} (2=abs count wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float; got " + type(result["f1"]).__name__


def test_full_class_coverage_returns_one() -> None:
    """fid covering all distinct classes -> ratio=1.0."""
    problems = [_p("A", "f1"), _p("B", "f1")]
    result = fid_class_coverage_ratio(problems)
    assert abs(result["f1"] - 1.0) < 1e-9, f"f1 covers all 2 classes -> 1.0; got {result['f1']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_class_coverage_ratio([]) == {}


def test_values_in_zero_to_one() -> None:
    """All ratios in (0, 1]."""
    problems = [_p("A", "f1"), _p("B", "f1"), _p("A", "f2")]
    result = fid_class_coverage_ratio(problems)
    for fid, ratio in result.items():
        assert 0.0 < ratio <= 1.0, f"Ratio for {fid} out of (0,1]: {ratio}"


def test_partial_coverage_correct_fraction() -> None:
    """Partial coverage gives correct fraction.

    3 total classes. fid 'f1' appears in 1 class -> ratio=1/3.
    """
    problems = [_p("A", "f1"), _p("B", "f2"), _p("C", "f3")]
    result = fid_class_coverage_ratio(problems)
    assert abs(result["f1"] - 1.0 / 3.0) < 1e-9, (
        f"f1 in 1 of 3 classes -> 0.333; got {result['f1']}"
    )
