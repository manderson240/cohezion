"""Item 691: fid_severity_ratio() -- fraction of problems matching severity per fid.

Fid-axis complement of class_severity_ratio (690).
fid_severity_ratio(problems, severity) -> dict[str, float].
Zero-inclusive.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID, denominator is per-fid total;
     fid 'f1': 4 problems (3 HIGH,1 LOW) -> ratio=3/4=0.75;
     class-outer wrong; global-denominator wrong.
  2. Ratio = 1.0 when all problems for fid match.
  3. Empty -> {}.
  4. Multiple fids, independent denominators.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_ratio


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_per_fid_denominator_primary_discriminator() -> None:
    """PRIMARY DISC.: key is FID, denominator is per-fid total.

    fid 'f1': 4 problems (3 HIGH, 1 LOW) -> ratio = 3/4 = 0.75.
    class-outer gives ratio keyed by 'A'; global-denominator gives wrong fraction.
    """
    problems = [_p("f1", "HIGH")] * 3 + [_p("f1", "LOW")] * 1
    result = fid_severity_ratio(problems, "HIGH")
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"'A' must NOT be key (fid-axis); got {list(result)}"
    assert abs(result["f1"] - 0.75) < 1e-9, (
        f"3/4=0.75; got {result['f1']:.6f} (class-outer/global-denom wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_ratio_one_when_all_match() -> None:
    """All problems for fid match -> ratio = 1.0."""
    problems = [_p("f2", "CRITICAL")] * 3
    result = fid_severity_ratio(problems, "CRITICAL")
    assert abs(result["f2"] - 1.0) < 1e-9, f"3/3=1.0; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_ratio([], "HIGH") == {}


def test_multiple_fids_independent_denominators() -> None:
    """Different fids use their own totals."""
    problems = [_p("f3", "HIGH")] * 2 + [_p("f3", "LOW")] * 2  # f3: 2/4 = 0.5
    problems += [_p("f4", "HIGH")] * 1 + [_p("f4", "LOW")] * 3  # f4: 1/4 = 0.25
    result = fid_severity_ratio(problems, "HIGH")
    assert abs(result["f3"] - 0.5) < 1e-9, f"f3: 2/4=0.5; got {result.get('f3')}"
    assert abs(result["f4"] - 0.25) < 1e-9, f"f4: 1/4=0.25; got {result.get('f4')}"


def test_return_type_is_float() -> None:
    """Result values must be float."""
    result = fid_severity_ratio([_p("f5", "HIGH"), _p("f5", "LOW")], "HIGH")
    assert isinstance(result["f5"], float), f"Must be float; got {type(result['f5'])}"
