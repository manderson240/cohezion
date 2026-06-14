"""Item 787: fid_severity_rank_high_fraction() -- fraction rank>=3 per fid.

fid_severity_rank_high_fraction(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_high_fraction (item 786).
fraction = count(rank >= 3) / n per fid.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [INFO*3,HIGH*2] -> 0.4;
     class-outer wrong; count-impl=2 wrong.
  2. All CRITICAL per fid -> 1.0.
  3. Multi-fid: each independently computed.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_high_fraction


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_key_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; fid f1: [INFO*3,HIGH*2] -> 0.4.

    class-outer wrong; count-impl=2 wrong.
    """
    problems = [_p("f1", "INFO")] * 3 + [_p("f1", "HIGH")] * 2
    result = fid_severity_rank_high_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.4, abs_tol=1e-9), f"[INFO*3,HIGH*2] -> 0.4; got {got}"
    assert not math.isclose(got, 2.0, abs_tol=1e-6), "Must be fraction not count (2)"


def test_all_critical_gives_one() -> None:
    """All CRITICAL per fid -> 1.0."""
    problems = [_p("f2", "CRITICAL")] * 4
    result = fid_severity_rank_high_fraction(problems)
    assert math.isclose(result["f2"], 1.0, abs_tol=1e-9), f"All CRITICAL -> 1.0; got {result['f2']}"


def test_multi_fid_independent() -> None:
    """Each fid's fraction is computed independently."""
    problems = (
        [_p("f3", "CRITICAL")] * 2
        + [_p("f3", "INFO")] * 2
        + [_p("f4", "LOW")] * 3
        + [_p("f4", "HIGH")]
    )
    result = fid_severity_rank_high_fraction(problems)
    # f3: 2/4=0.5; f4: 1/4=0.25
    assert math.isclose(result["f3"], 0.5, abs_tol=1e-9), (
        f"f3: [CRIT*2,INFO*2] -> 0.5; got {result['f3']}"
    )
    assert math.isclose(result["f4"], 0.25, abs_tol=1e-9), (
        f"f4: [LOW*3,HIGH] -> 0.25; got {result['f4']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_high_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f5", "HIGH"), _p("f5", "INFO")]
    result = fid_severity_rank_high_fraction(problems)
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
