"""Item 752: fid_severity_rank_dominant_ratio() -- modal severity rank fraction per fid.

fid_severity_rank_dominant_ratio(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_dominant_ratio (item 751).
dominant_ratio = count(majority_rank) / n per fid.
All-same -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND ratio not count;
     fid f1: INFO(0)*2+CRITICAL(4) -> ratio=2/3~0.667; class-outer gives 'A' wrong;
     count-impl gives 2 wrong; rank-impl gives 0 wrong.
  2. All-same -> 1.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_dominant_ratio


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_ratio_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND ratio=2/3; count=2 wrong; rank=0 wrong.

    fid f1: INFO(0)*2+CRITICAL(4) -> majority=0 (count 2 vs 1); ratio=2/3.
    class-outer gives key='A' wrong.
    """
    problems = [_p("f1", "INFO"), _p("f1", "INFO"), _p("f1", "CRITICAL")]
    result = fid_severity_rank_dominant_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class must NOT be key; got {list(result)}"
    got = result["f1"]
    expected = 2 / 3
    assert math.isclose(got, expected, abs_tol=1e-9), (
        f"INFO*2+CRITICAL -> ratio=2/3~{expected:.6f}; got {repr(got)} "
        f"(count=2 wrong, rank=0 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_all_same_gives_one() -> None:
    """All-same severity -> dominant_ratio=1.0."""
    problems = [_p("f2", "CRITICAL")] * 4
    result = fid_severity_rank_dominant_ratio(problems)
    got = result.get("f2")
    assert math.isclose(got, 1.0, abs_tol=1e-9), f"All CRITICAL -> ratio=1.0; got {repr(got)}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_dominant_ratio([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = (
        [_p("f3", "INFO"), _p("f3", "INFO"), _p("f3", "CRITICAL")]  # ratio=2/3
        + [_p("f4", "HIGH")] * 3  # all-same -> 1.0
    )
    result = fid_severity_rank_dominant_ratio(problems)
    assert math.isclose(result["f3"], 2 / 3, abs_tol=1e-9), (
        f"f3 -> ratio=2/3; got {repr(result.get('f3'))}"
    )
    assert math.isclose(result["f4"], 1.0, abs_tol=1e-9), (
        f"f4 all-same -> 1.0; got {repr(result.get('f4'))}"
    )


def test_return_type_is_float() -> None:
    """Result values must be float."""
    result = fid_severity_rank_dominant_ratio([_p("f5", "INFO"), _p("f5", "HIGH")])
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
