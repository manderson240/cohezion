"""Item 725: fid_severity_rank_std() -- population std dev of severity ranks per fid.

fid_severity_rank_std(problems) -> dict[str, float].
Fid-axis complement of class_severity_rank_std (item 724).
Single-problem fid -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND returns std dev (not variance);
     fid 'f1': CRITICAL(4)+INFO(0) -> std=2.0; class-outer gives key='A' wrong;
     variance-impl gives 4.0 wrong.
  2. Single-problem fid -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_std


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_std_not_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND std dev not variance.

    fid 'f1': CRITICAL(4)+INFO(0) -> std=2.0 (not variance=4.0).
    class-outer gives key='A' wrong; variance-impl gives 4.0 wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "INFO")]
    result = fid_severity_rank_std(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    assert math.isclose(result["f1"], 2.0, abs_tol=1e-9), (
        f"CRIT(4)+INFO(0): std=2.0; got {result['f1']} (variance-impl=4.0 wrong)"
    )


def test_single_problem_gives_zero() -> None:
    """Single-problem fid -> 0.0."""
    result = fid_severity_rank_std([_p("f2", "HIGH")])
    assert math.isclose(result["f2"], 0.0, abs_tol=1e-9), (
        f"Single HIGH -> 0.0; got {result.get('f2')}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_std([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid computes independently."""
    problems = [_p("f3", "CRITICAL"), _p("f3", "CRITICAL")]  # f3: [4,4] -> 0.0
    problems += [_p("f4", "HIGH"), _p("f4", "LOW")]  # f4: [3,1] -> 1.0
    result = fid_severity_rank_std(problems)
    assert math.isclose(result["f3"], 0.0, abs_tol=1e-9), (
        f"f3: both CRIT -> 0.0; got {result.get('f3')}"
    )
    assert math.isclose(result["f4"], 1.0, abs_tol=1e-9), (
        f"f4: HIGH+LOW -> 1.0; got {result.get('f4')}"
    )


def test_return_type_is_float() -> None:
    """Result values must be float."""
    result = fid_severity_rank_std([_p("f5", "HIGH"), _p("f5", "LOW")])
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
