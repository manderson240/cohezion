"""Item 725: fid_severity_rank_std() -- population std dev of severity ranks per fid.

Fid-axis complement of class_severity_rank_std (item 724).
fid_severity_rank_std(problems) -> dict[str, float].
Single-problem -> 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, std dev not variance;
     fid 'f1': CRITICAL(4)+INFO(0) -> std=2.0;
     class-outer wrong; variance=4.0 wrong.
  2. Single problem -> 0.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Uniform ranks -> 0.0.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_std


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_std_not_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID AND std dev not variance.

    fid 'f1': CRITICAL(4)+INFO(0) -> std=2.0 (mean=2, var=4, sqrt=2).
    class-outer wrong (key='A'); variance-impl gives 4.0 wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "INFO")]
    result = fid_severity_rank_std(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert abs(result["f1"] - 2.0) < 1e-9, (
        f"CRITICAL(4)+INFO(0) -> std=2.0; got {result['f1']} (variance=4.0 wrong)"
    )
    assert isinstance(result["f1"], float), f"Must be float; got {type(result['f1'])}"


def test_single_problem_gives_zero() -> None:
    """Single problem per fid -> std = 0.0."""
    problems = [_p("f2", "MEDIUM")]
    result = fid_severity_rank_std(problems)
    assert result["f2"] == 0.0, f"Single problem -> std=0.0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_std([]) == {}


def test_multiple_fids_independent() -> None:
    """Each fid std computed independently."""
    problems = [_p("f3", "CRITICAL")] * 3  # f3: uniform -> std=0.0
    problems += [_p("f4", "CRITICAL"), _p("f4", "INFO")]  # f4: std=2.0
    result = fid_severity_rank_std(problems)
    assert abs(result["f3"] - 0.0) < 1e-9, f"f3 uniform -> std=0.0; got {result.get('f3')}"
    assert abs(result["f4"] - 2.0) < 1e-9, f"f4 CRIT+INFO -> std=2.0; got {result.get('f4')}"


def test_three_values_std() -> None:
    """Three ranks: HIGH(3)+MEDIUM(2)+LOW(1) -> std=sqrt(2/3)."""
    problems = [_p("f5", "HIGH"), _p("f5", "MEDIUM"), _p("f5", "LOW")]
    result = fid_severity_rank_std(problems)
    expected = math.sqrt(2 / 3)
    assert abs(result["f5"] - expected) < 1e-9, (
        f"HIGH+MED+LOW -> std={expected:.6f}; got {result.get('f5')}"
    )
