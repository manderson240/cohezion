"""Item 753: class_severity_rank_minority_ratio() -- fraction NOT at the majority rank per class.

class_severity_rank_minority_ratio(problems) -> dict[str, float].
minority_ratio = 1.0 - dominant_ratio = (n - count(majority_rank)) / n.
All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: minority is 1-dominant (not count); class A: INFO(0)*2+CRITICAL(4)
     -> majority=0, minority=1/3~0.333; count-impl gives 1 wrong; zero-impl gives 0.0 wrong.
  2. All-same -> 0.0 (no minority).
  3. Symmetric complement: minority + dominant = 1.0 exactly.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_severity_rank_minority_ratio,
    class_severity_rank_dominant_ratio,
)


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_minority_not_count_primary_discriminator() -> None:
    """PRIMARY DISC.: minority=1/3~0.333; count-impl gives 1 wrong; zero-impl gives 0.0 wrong.

    class A: INFO(0)*2+CRITICAL(4) -> majority=0 (count=2), minority=1/3.
    """
    problems = [_p("A", "INFO"), _p("A", "INFO"), _p("A", "CRITICAL")]
    result = class_severity_rank_minority_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be key; got {list(result)}"
    got = result["A"]
    assert math.isclose(got, 1 / 3, abs_tol=1e-9), (
        f"INFO*2+CRITICAL: minority=1/3~{1/3:.6f}; got {got}"
    )
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "Must be minority not count"
    assert not math.isclose(got, 0.0, abs_tol=1e-6), "Must not be zero"


def test_all_same_gives_zero() -> None:
    """All same -> minority_ratio = 0.0 (everyone is at the majority rank)."""
    problems = [_p("B", "CRITICAL")] * 4
    result = class_severity_rank_minority_ratio(problems)
    got = result.get("B")
    assert got is not None and math.isclose(got, 0.0, abs_tol=1e-9), (
        f"All CRITICAL -> 0.0; got {got}"
    )


def test_complement_of_dominant_ratio() -> None:
    """minority_ratio + dominant_ratio == 1.0 for any distribution."""
    problems = [_p("C", "INFO"), _p("C", "HIGH"), _p("C", "INFO"), _p("C", "CRITICAL")]
    minority = class_severity_rank_minority_ratio(problems)["C"]
    dominant = class_severity_rank_dominant_ratio(problems)["C"]
    assert math.isclose(minority + dominant, 1.0, abs_tol=1e-9), (
        f"minority({minority}) + dominant({dominant}) must == 1.0"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_severity_rank_minority_ratio([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("D", "INFO"), _p("D", "INFO"), _p("D", "CRITICAL")]
    result = class_severity_rank_minority_ratio(problems)
    assert isinstance(result["D"], float), f"Must be float; got {type(result['D'])}"
