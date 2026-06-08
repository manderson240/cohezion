"""Item 749: fid_severity_rank_concentration() -- HHI of severity rank distribution per fid.

fid_severity_rank_concentration(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_concentration (item 748).
HHI = sum(p_k^2) where p_k = count(rank=k)/n.
All-same -> 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND HHI!=entropy; fid 'f1': INFO(0)*3+HIGH(3)*2 ->
     HHI=0.52; class-outer gives 'A' wrong; entropy-impl gives ~0.971 wrong.
  2. All-same -> HHI=1.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_concentration


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_hhi_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND HHI=0.52 not entropy.

    fid 'f1': INFO(0)*3+HIGH(3)*2 -> p(0)=0.6, p(3)=0.4; HHI=0.52.
    class-outer gives key='A' wrong; entropy-impl gives ~0.971 wrong.
    """
    problems = [
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "HIGH"),
        _p("f1", "HIGH"),
    ]
    result = fid_severity_rank_concentration(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.52, abs_tol=1e-9), (
        f"f1: [0.6,0.4] -> HHI=0.52; got {repr(got)} (entropy~0.971 wrong)"
    )
    assert isinstance(got, float), f"Must be float; got {type(got)}"


def test_all_same_gives_one() -> None:
    """All-same severity -> HHI=1.0."""
    problems = [_p("f2", "CRITICAL")] * 4
    result = fid_severity_rank_concentration(problems)
    got = result.get("f2")
    assert math.isclose(got, 1.0, abs_tol=1e-9), f"All CRITICAL -> HHI=1.0; got {repr(got)}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_concentration([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = [
        _p("f3", "INFO"),
        _p("f3", "INFO"),
        _p("f3", "INFO"),
        _p("f3", "HIGH"),
        _p("f3", "HIGH"),
    ] + [_p("f4", "MEDIUM")] * 3
    result = fid_severity_rank_concentration(problems)
    assert math.isclose(result["f3"], 0.52, abs_tol=1e-9), (
        f"f3 -> HHI=0.52; got {repr(result.get('f3'))}"
    )
    assert math.isclose(result["f4"], 1.0, abs_tol=1e-9), (
        f"f4 all-same -> HHI=1.0; got {repr(result.get('f4'))}"
    )


def test_return_type_is_float() -> None:
    """Result values must be float."""
    result = fid_severity_rank_concentration([_p("f5", "INFO"), _p("f5", "HIGH")])
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
