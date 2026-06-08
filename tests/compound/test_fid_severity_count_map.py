"""Item 679: fid_severity_count_map() -- 2D cross-tab of fid x severity counts.

Fid-axis complement of class_severity_count_map (item 678).
Returns {fid: {severity: count}}.  Sparse 2D nested dict.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID not class; fid 'f1': 3 HIGH + 2 LOW -> result['f1']['HIGH']=3.
     Kills class-outer impl (item 678 copy).
  2. Sparse: missing severities absent from inner dict.
  3. Empty -> {}.
  4. Multiple fids get independent severity counts.
  5. Different fids in same class are counted separately.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_count_map


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_key_not_class_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID NOT class.

    fid 'f1': 3 HIGH + 2 LOW -> result['f1']['HIGH']=3, result['f1']['LOW']=2.
    Class-outer impl would give result['A']['HIGH']=3 wrong.
    """
    problems = [_p("f1", "HIGH")] * 3 + [_p("f1", "LOW")] * 2
    result = fid_severity_count_map(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"Fid 'f1' must be outer key; got {list(result)}"
    assert isinstance(result["f1"], dict), f"Inner must be dict; got {type(result['f1'])}"
    assert result["f1"]["HIGH"] == 3, f"3 HIGH -> count=3; got {result['f1'].get('HIGH')}"
    assert result["f1"]["LOW"] == 2, f"2 LOW -> count=2; got {result['f1'].get('LOW')}"


def test_sparse_missing_severities_absent() -> None:
    """Missing severities are absent from inner dict."""
    problems = [_p("fx", "CRITICAL")] * 2
    result = fid_severity_count_map(problems)
    assert result["fx"]["CRITICAL"] == 2
    assert "HIGH" not in result["fx"], f"HIGH must be absent; got {result['fx']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_count_map([]) == {}


def test_multiple_fids_independent() -> None:
    """Different fids get independent severity counts."""
    problems = [
        Problem(problem_class="A", finding_id="f1", severity="HIGH"),
        Problem(problem_class="A", finding_id="f1", severity="HIGH"),
        Problem(problem_class="B", finding_id="f2", severity="LOW"),
        Problem(problem_class="B", finding_id="f2", severity="LOW"),
        Problem(problem_class="B", finding_id="f2", severity="LOW"),
    ]
    result = fid_severity_count_map(problems)
    assert result["f1"]["HIGH"] == 2, f"f1/HIGH=2; got {result.get('f1', {}).get('HIGH')}"
    assert "LOW" not in result.get("f1", {}), "f1 has no LOW"
    assert result["f2"]["LOW"] == 3, f"f2/LOW=3; got {result.get('f2', {}).get('LOW')}"


def test_same_fid_across_classes_aggregated() -> None:
    """Same fid in different classes -> severities aggregated into one fid entry."""
    problems = [
        Problem(problem_class="A", finding_id="f1", severity="HIGH"),
        Problem(problem_class="B", finding_id="f1", severity="LOW"),
    ]
    result = fid_severity_count_map(problems)
    # fid 'f1' spans class A and B — both should be in result['f1']
    assert result["f1"]["HIGH"] == 1
    assert result["f1"]["LOW"] == 1
