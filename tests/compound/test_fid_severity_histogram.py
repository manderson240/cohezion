"""Item 585: fid_severity_histogram() — raw severity count histogram per fid (2026-06-08).

``fid_severity_histogram(problems) -> dict[str, dict[str, int]]``:
Returns {fid: {severity: count}}.  FID-axis complement of class_severity_histogram.
Fids absent from problems are absent from result.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: outer dict keyed by FID (not class name).
     One class 'A', two fids 'f1' and 'f2': result keys are fid names, not 'A'.
     class_severity_histogram would give {'A': {sev: count}} (wrong outer key).
     Kills impl reusing class_severity_histogram on wrong axis.
  2. Inner dict keyed by SEVERITY labels (not fid names).
     fid 'fx' with [CRITICAL, LOW] -> result['fx'] == {'CRITICAL': 1, 'LOW': 1}.
     Kills impl using fid as inner key (giving {'fx': {'fx': 2}}).
  3. Count values are int (not float).
     Kills impl returning float counts.
  4. Empty problems -> {} (not raise).
     Kills impl without empty guard.
  5. Multiple fids with independent histograms.
     f1=[HIGH,HIGH,HIGH] -> {'HIGH':3}; f2=[LOW,CRITICAL] -> {'LOW':1,'CRITICAL':1}.
     f1 must not contain LOW; f2 must not contain HIGH.
     Kills impl computing aggregate across all fids.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_histogram


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_keyed_by_fid_not_class_primary_discriminator() -> None:
    """PRIMARY DISC.: outer dict keyed by FID (not class name).

    One class 'A', fid 'f1'=[HIGH,HIGH] and fid 'f2'=[LOW]:
    result keys must be 'f1', 'f2' (NOT 'A').
    class_severity_histogram gives {'A': {sev:count}} (class axis).
    Kills impl reusing class_severity_histogram on wrong axis.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "LOW"),
    ]
    result = fid_severity_histogram(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, (
        f"Outer dict must be keyed by fid 'f1'; got keys={list(result)} "
        f"('A' present = class axis wrong)"
    )
    assert "f2" in result, f"fid 'f2' must be in result; got keys={list(result)}"
    assert "A" not in result, f"Outer dict must NOT be keyed by class 'A'; got {result}"
    assert result["f1"] == {"HIGH": 2}, f"f1: {{HIGH:2}}; got {result['f1']}"
    assert result["f2"] == {"LOW": 1}, f"f2: {{LOW:1}}; got {result['f2']}"


def test_inner_dict_keyed_by_severity_not_fid() -> None:
    """Inner dict keyed by SEVERITY labels (not fid names).

    fid 'fx' with problems from classes A and B, severities CRITICAL and LOW:
    result['fx'] must be {'CRITICAL': 1, 'LOW': 1}, NOT {'fx': 2}.
    Kills impl using fid as inner key.
    """
    problems = [_p("A", "fx", "CRITICAL"), _p("B", "fx", "LOW")]
    result = fid_severity_histogram(problems)
    inner = result.get("fx", {})
    assert "CRITICAL" in inner, f"Inner dict must be keyed by severity 'CRITICAL'; got {inner}"
    assert "LOW" in inner, f"Inner dict must contain 'LOW'; got {inner}"
    assert "fx" not in inner, f"Inner dict must NOT be keyed by fid name; got {inner}"
    assert inner["CRITICAL"] == 1, f"CRITICAL count=1; got {inner['CRITICAL']}"
    assert inner["LOW"] == 1, f"LOW count=1; got {inner['LOW']}"


def test_count_values_are_int() -> None:
    """Count values are int (not float).

    Kills impl returning float counts.
    """
    problems = [_p("A", "fa", "HIGH"), _p("B", "fa", "HIGH")]
    result = fid_severity_histogram(problems)
    count = result["fa"]["HIGH"]
    assert isinstance(count, int), f"Count must be int; got {type(count).__name__}"
    assert count == 2, f"2 HIGH -> count=2; got {count}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = fid_severity_histogram([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_multiple_fids_independent_histograms() -> None:
    """Multiple fids have independent histograms.

    f1 = [HIGH, HIGH, HIGH] -> {'HIGH': 3}.
    f2 = [LOW, CRITICAL]    -> {'LOW': 1, 'CRITICAL': 1}.
    f1 must not contain LOW; f2 must not contain HIGH.
    Kills impl computing a flat aggregate across all fids.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("B", "f1", "HIGH"),
        _p("C", "f1", "HIGH"),
        _p("A", "f2", "LOW"),
        _p("B", "f2", "CRITICAL"),
    ]
    result = fid_severity_histogram(problems)
    assert result.get("f1") == {"HIGH": 3}, f"f1: {{HIGH:3}}; got {result.get('f1')}"
    assert result.get("f2") == {"LOW": 1, "CRITICAL": 1}, (
        f"f2: {{LOW:1, CRITICAL:1}}; got {result.get('f2')}"
    )
    assert "LOW" not in result["f1"], "f1 must not contain f2's LOW label"
    assert "HIGH" not in result["f2"], "f2 must not contain f1's HIGH label"
