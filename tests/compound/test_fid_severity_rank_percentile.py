"""Item 721: fid_severity_rank_percentile() -- fraction at-or-below severity rank per fid.

Fid-axis complement of class_severity_rank_percentile (item 720).
fid_severity_rank_percentile(problems, severity) -> dict[str, float].
[0.0, 1.0].  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, fraction at-or-below;
     fid 'f1': CRITICAL+HIGH+LOW, severity='HIGH' -> 2/3;
     class-outer wrong; above-impl wrong; count wrong.
  2. All at or below -> 1.0.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_percentile


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_at_or_below_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID, fraction at-or-below rank(HIGH)=3.

    fid 'f1': CRITICAL(4)+HIGH(3)+LOW(1), severity='HIGH'.
    HIGH(3)<=3 and LOW(1)<=3 counted; CRITICAL(4)>3 not counted -> 2/3.
    class-outer wrong; above-impl wrong.
    """
    problems = [_p("f1", "CRITICAL"), _p("f1", "HIGH"), _p("f1", "LOW")]
    result = fid_severity_rank_percentile(problems, "HIGH")
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert abs(result["f1"] - 2 / 3) < 1e-9, f"HIGH+LOW <= rank(HIGH) -> 2/3; got {result['f1']}"
    assert isinstance(result["f1"], float), f"Must be float; got {type(result['f1'])}"


def test_all_at_or_below_gives_one() -> None:
    """All at or below threshold -> 1.0."""
    problems = [_p("f2", "INFO"), _p("f2", "LOW"), _p("f2", "MEDIUM")]
    result = fid_severity_rank_percentile(problems, "CRITICAL")
    assert abs(result["f2"] - 1.0) < 1e-9, f"All <= CRITICAL rank -> 1.0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_percentile([], "HIGH") == {}


def test_multiple_fids_independent() -> None:
    """Each fid computed independently."""
    problems = [_p("f3", "HIGH"), _p("f3", "CRITICAL")]  # f3: HIGH<=3 -> 1/2
    problems += [_p("f4", "LOW"), _p("f4", "LOW")]  # f4: both LOW<=3 -> 1.0
    result = fid_severity_rank_percentile(problems, "HIGH")
    assert abs(result["f3"] - 0.5) < 1e-9, f"f3: 1/2 -> 0.5; got {result.get('f3')}"
    assert abs(result["f4"] - 1.0) < 1e-9, f"f4: 2/2 -> 1.0; got {result.get('f4')}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    problems = [_p("f5", "HIGH")]
    result = fid_severity_rank_percentile(problems, "HIGH")
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
    assert abs(result["f5"] - 1.0) < 1e-9, f"Single HIGH at rank(HIGH) -> 1.0; got {result['f5']}"
