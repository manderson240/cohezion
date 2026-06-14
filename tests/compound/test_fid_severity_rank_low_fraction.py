"""Item 791: fid_severity_rank_low_fraction() -- fraction rank<=1 (INFO/LOW) per fid.

fid_severity_rank_low_fraction(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_low_fraction (item 790).
fraction = count(rank <= 1) / n per fid.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID; fid f1: [INFO*2,LOW*1,MEDIUM*2] -> 0.6;
     class-outer wrong; 1-high_frac=1.0 wrong.
  2. MEDIUM does not count as low (rank 2 > 1).
  3. Multi-fid independent counts.
  4. Empty -> {}.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_low_fraction


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="X", finding_id=fid, severity=sev)


def test_fid_outer_key_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; fid f1: [INFO*2,LOW*1,MEDIUM*2] -> 0.6."""
    problems = [_p("f1", "INFO")] * 2 + [_p("f1", "LOW")] + [_p("f1", "MEDIUM")] * 2
    result = fid_severity_rank_low_fraction(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 0.6, abs_tol=1e-9), f"[INFO*2,LOW*1,MED*2] -> 0.6; got {got}"
    assert not math.isclose(got, 1.0, abs_tol=1e-6), "MEDIUM must not be counted"


def test_medium_does_not_count_as_low() -> None:
    """MEDIUM (rank=2) above threshold; not counted as low."""
    problems = [_p("f2", "MEDIUM")] * 4 + [_p("f2", "LOW")] * 1
    result = fid_severity_rank_low_fraction(problems)
    got = result["f2"]
    assert math.isclose(got, 0.2, abs_tol=1e-9), f"[MED*4,LOW*1] -> 0.2; got {got}"


def test_multi_fid_independent() -> None:
    """Each fid's fraction independently computed."""
    problems = (
        [_p("f3", "INFO")] * 2 + [_p("f3", "CRITICAL")] + [_p("f4", "LOW")] * 2 + [_p("f4", "HIGH")]
    )
    result = fid_severity_rank_low_fraction(problems)
    # f3: 2/3~0.667; f4: 2/3~0.667
    assert math.isclose(result["f3"], 2 / 3, abs_tol=1e-9), (
        f"f3: [INFO*2,CRIT] -> 2/3; got {result['f3']}"
    )
    assert math.isclose(result["f4"], 2 / 3, abs_tol=1e-9), (
        f"f4: [LOW*2,HIGH] -> 2/3; got {result['f4']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_low_fraction([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f5", "INFO"), _p("f5", "CRITICAL")]
    result = fid_severity_rank_low_fraction(problems)
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
