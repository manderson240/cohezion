"""Item 765: class_severity_rank_p25() -- 25th percentile of severity ranks per class.

class_severity_rank_p25(problems) -> dict[str, float].
25th percentile using linear interpolation:
i = 0.25*(n-1); p25 = sorted[floor(i)] + frac*(sorted[ceil(i)] - sorted[floor(i)]).
All-same -> that rank as float.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: p25 not median; [INFO,LOW,MEDIUM,HIGH,CRITICAL]
     -> sorted=[0,1,2,3,4]; i=0.25*4=1 (exact); p25=sorted[1]=1.0;
     median-impl gives 2.0 wrong; min-impl gives 0.0 wrong.
  2. All-same -> same rank as float.
  3. Interpolation: [LOW(1),HIGH(3)] -> i=0.25*1=0.25; p25=1+0.25*(3-1)=1.5.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, class_severity_rank_p25


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_p25_not_median_primary_discriminator() -> None:
    """PRIMARY DISC.: p25=1.0; median=2.0 wrong; min=0.0 wrong.

    class A: [INFO,LOW,MEDIUM,HIGH,CRITICAL] -> sorted=[0,1,2,3,4];
    i=0.25*4=1 (exact); p25=sorted[1]=1.0.
    """
    problems = [_p("A", sev) for sev in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = class_severity_rank_p25(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 1.0, abs_tol=1e-9), f"[0,1,2,3,4]: p25=1.0; got {got}"
    assert not math.isclose(got, 2.0, abs_tol=1e-6), "Must be p25 not median"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must be p25 not min"


def test_all_same_gives_same_rank() -> None:
    """All same -> p25 = that rank as float."""
    problems = [_p("B", "HIGH")] * 4
    result = class_severity_rank_p25(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 3.0, abs_tol=1e-9), (
        f"All HIGH(rank=3) -> p25=3.0; got {got}"
    )


def test_interpolation_two_values() -> None:
    """[LOW(1), HIGH(3)]: i=0.25, p25=1+0.25*(3-1)=1.5."""
    problems = [_p("C", "LOW"), _p("C", "HIGH")]
    result = class_severity_rank_p25(problems)
    got = result.get("C")
    assert got is not None and math.isclose(got, 1.5, abs_tol=1e-9), (
        f"[1,3]: i=0.25, p25=1.5; got {got}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_p25([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", sev) for sev in ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]]
    result = class_severity_rank_p25(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
