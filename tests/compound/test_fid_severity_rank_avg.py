"""Item 697: fid_severity_rank_avg() -- mean severity rank per fid.

Fid-axis complement of class_severity_rank_avg (696).
fid_severity_rank_avg(problems) -> dict[str, float].
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, value is avg rank;
     fid 'f1': HIGH(3)+LOW(1)+INFO(0) -> avg=(3+1+0)/3≈1.333;
     class-outer wrong; rank_sum-impl gives 4 wrong.
  2. Single problem -> avg = its rank.
  3. Empty -> {}.
  4. Multiple fids, independent.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_avg


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_avg_rank_primary_discriminator() -> None:
    """PRIMARY DISC.: key is FID, value is mean rank.

    fid 'f1': HIGH(3)+LOW(1)+INFO(0) -> avg = (3+1+0)/3 = 4/3 ≈ 1.333.
    class-outer wrong (keys by 'A'); rank_sum-impl gives 4 wrong.
    """
    problems = [_p("f1", "HIGH"), _p("f1", "LOW"), _p("f1", "INFO")]
    result = fid_severity_rank_avg(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    expected = (3 + 1 + 0) / 3
    assert abs(result["f1"] - expected) < 1e-9, (
        f"(3+1+0)/3={expected:.4f}; got {result['f1']:.4f} (rank_sum=4 wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_single_problem_avg_equals_rank() -> None:
    """Single problem -> avg = its rank."""
    problems = [_p("f2", "CRITICAL")]
    result = fid_severity_rank_avg(problems)
    assert abs(result["f2"] - 4.0) < 1e-9, f"CRITICAL alone -> 4.0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_avg([]) == {}


def test_multiple_fids_independent() -> None:
    """Different fids use their own problem counts."""
    problems = (
        [_p("f3", "HIGH"), _p("f3", "HIGH")]  # f3: (3+3)/2=3.0
        + [_p("f4", "LOW"), _p("f4", "INFO"), _p("f4", "INFO")]  # f4: (1+0+0)/3≈0.333
    )
    result = fid_severity_rank_avg(problems)
    assert abs(result["f3"] - 3.0) < 1e-9, f"f3: (3+3)/2=3.0; got {result.get('f3')}"
    expected_f4 = (1 + 0 + 0) / 3
    assert abs(result["f4"] - expected_f4) < 1e-9, f"f4: 1/3≈0.333; got {result.get('f4')}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    result = fid_severity_rank_avg([_p("f5", "HIGH"), _p("f5", "LOW")])
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
