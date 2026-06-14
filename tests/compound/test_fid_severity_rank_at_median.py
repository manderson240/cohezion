"""Item 762: fid_severity_rank_at_median() -- fraction at median rank per fid.

fid_severity_rank_at_median(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_at_median (item 761).
fraction = count(rank == median) / n per fid.
All-same -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: INFO*2+CRITICAL -> at=2/3;
     class-outer gives 'A' wrong; above-impl gives 1/3 wrong.
  2. All-same -> 1.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_at_median


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_at_median_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; at=2/3; above=1/3 wrong; class-outer wrong.

    fid f1: INFO(0)*2+CRITICAL(4) -> sorted=[0,0,4], median=0, at-count=2, frac=2/3.
    """
    problems = [_p("f1", "INFO"), _p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_at_median(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 2 / 3, abs_tol=1e-9), (
        f"INFO*2+CRITICAL -> at=2/3~{2 / 3:.6f}; got {got}"
    )


def test_all_same_gives_one() -> None:
    """All same -> at_median = 1.0."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_rank_at_median(problems)
    got = result.get("f2")
    assert got is not None and math.isclose(got, 1.0, abs_tol=1e-9), (
        f"All CRITICAL -> 1.0; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_at_median([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = [
        _p("fA", "INFO"),
        _p("fA", "INFO"),
        _p("fA", "CRITICAL"),  # at=2/3
        _p("fB", "HIGH"),
        _p("fB", "HIGH"),
        _p("fB", "HIGH"),  # all-same -> 1.0
    ]
    result = fid_severity_rank_at_median(problems)
    assert math.isclose(result["fA"], 2 / 3, abs_tol=1e-9), f"fA -> 2/3; got {result['fA']}"
    assert math.isclose(result["fB"], 1.0, abs_tol=1e-9), f"fB -> 1.0; got {result['fB']}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "INFO"), _p("f3", "INFO"), _p("f3", "HIGH")]
    result = fid_severity_rank_at_median(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"
