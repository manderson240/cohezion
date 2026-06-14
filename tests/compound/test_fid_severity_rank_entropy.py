"""Item 745: fid_severity_rank_entropy() -- Shannon entropy of severity rank distribution per fid.

fid_severity_rank_entropy(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_entropy (item 744).
H = -sum(p_k * log2(p_k)).  All-same -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND H=1.0 for balanced ranks;
     fid 'f1': INFO×2+HIGH×2 -> H=1.0; class-outer wrong; count=4 wrong.
  2. All-same -> 0.0.
  3. Empty -> {}.
  4. Return type is float.
  5. Multiple fids independent.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_entropy


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_entropy_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND H=1.0 for balanced ranks.

    fid 'f1': INFO×2+HIGH×2 -> H=1.0; class-outer gives key='A' wrong.
    """
    problems = [_p("f1", "INFO"), _p("f1", "INFO"), _p("f1", "HIGH"), _p("f1", "HIGH")]
    result = fid_severity_rank_entropy(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert math.isclose(got, 1.0, abs_tol=1e-9), f"INFO×2+HIGH×2 -> H=1.0; got {got}"


def test_all_same_gives_zero() -> None:
    """All-same severity -> H=0.0."""
    problems = [_p("f2", "CRITICAL")] * 4
    result = fid_severity_rank_entropy(problems)
    got = result.get("f2")
    assert math.isclose(got, 0.0, abs_tol=1e-9), f"All CRITICAL -> H=0.0; got {got}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_entropy([]) == {}


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f3", "INFO"), _p("f3", "HIGH")]
    result = fid_severity_rank_entropy(problems)
    assert isinstance(result["f3"], float), f"Must be float; got {type(result['f3'])}"


def test_multiple_fids_independent() -> None:
    """Multiple fids computed independently."""
    problems = [_p("fa", "INFO"), _p("fa", "INFO"), _p("fa", "HIGH"), _p("fa", "HIGH")] + [
        _p("fb", "MEDIUM")
    ] * 3
    result = fid_severity_rank_entropy(problems)
    assert math.isclose(result["fa"], 1.0, abs_tol=1e-9), f"fa -> H=1.0; got {result['fa']}"
    assert math.isclose(result["fb"], 0.0, abs_tol=1e-9), (
        f"fb all-same -> H=0.0; got {result['fb']}"
    )
