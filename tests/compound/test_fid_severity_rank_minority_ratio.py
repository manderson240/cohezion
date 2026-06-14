"""Item 754: fid_severity_rank_minority_ratio() -- fraction NOT at majority rank per fid.

fid_severity_rank_minority_ratio(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_minority_ratio (item 753).
minority_ratio = 1.0 - dominant_ratio per fid.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: INFO(0)*2+CRITICAL(4)
     -> minority=1/3~0.333; class-outer gives 'A' wrong; zero-impl gives 0.0 wrong.
  2. All-same -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_minority_ratio


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_minority_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; minority=1/3; class-outer wrong; zero wrong.

    fid f1: INFO(0)*2+CRITICAL(4) -> majority=0, minority=1/3~0.333.
    """
    problems = [_p("f1", "INFO"), _p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_minority_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 1 / 3, abs_tol=1e-9), (
        f"INFO*2+CRITICAL -> minority=1/3~{1 / 3:.6f}; got {got}"
    )


def test_all_same_gives_zero() -> None:
    """All same severity -> minority_ratio = 0.0."""
    problems = [_p("f2", "HIGH")] * 3
    result = fid_severity_rank_minority_ratio(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), f"All HIGH -> 0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_minority_ratio([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = [
        _p("fA", "INFO"),
        _p("fA", "INFO"),
        _p("fA", "CRITICAL"),  # minority=1/3
        _p("fB", "LOW"),
        _p("fB", "LOW"),
        _p("fB", "LOW"),  # all-same -> 0.0
    ]
    result = fid_severity_rank_minority_ratio(problems)
    assert math.isclose(result["fA"], 1 / 3, abs_tol=1e-9), f"fA -> 1/3; got {result['fA']}"
    assert math.isclose(result["fB"], 0.0, abs_tol=1e-9), f"fB -> 0.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "INFO"), _p("f3", "INFO"), _p("f3", "HIGH")]
    result = fid_severity_rank_minority_ratio(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
