"""Item 669: class_fid_min_severity() -- least severe label per class x fid cell.

Complement of class_fid_max_severity (item 668).
Returns {class: {fid: min_severity_str}}.
Severity order: CRITICAL > HIGH > MEDIUM > LOW > INFO (min = lowest rank).
str.  Sparse.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_min_severity


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_min_not_max_primary_discriminator() -> None:
    """PRIMARY DISC.: returns MINIMUM severity (NOT maximum, NOT count).

    Class A, fid 'f1': CRIT,CRIT,CRIT,LOW -> min='LOW' (max='CRITICAL' wrong).
    Kills max impl (the most natural wrong impl after seeing item 668).
    """
    problems = [_p("A", "f1", "CRITICAL")] * 3 + [_p("A", "f1", "LOW")]
    result = class_fid_min_severity(problems)
    assert isinstance(result, dict), "Outer must be dict"
    assert "A" in result
    assert "f1" in result["A"]
    assert result["A"]["f1"] == "LOW", (
        f"CRIT,CRIT,CRIT,LOW -> min='LOW'; got {result['A']['f1']} (max='CRITICAL' wrong)"
    )
    assert isinstance(result["A"]["f1"], str), "Must be str"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_min_severity([]) == {}


def test_single_problem_min_is_itself() -> None:
    """Single problem -> min = its own severity."""
    problems = [_p("A", "f2", "HIGH")]
    result = class_fid_min_severity(problems)
    assert result["A"]["f2"] == "HIGH"


def test_min_ordering_info_beats_low() -> None:
    """INFO is lowest rank; beats LOW for minimum."""
    problems = [_p("X", "f3", "LOW")] * 4 + [_p("X", "f3", "INFO")]
    result = class_fid_min_severity(problems)
    assert result["X"]["f3"] == "INFO", f"4 LOW + 1 INFO -> min='INFO'; got {result['X'].get('f3')}"


def test_multiple_cells_independent_minima() -> None:
    """Different cells get independent min severity."""
    problems = (
        [_p("A", "f4", "CRITICAL")] * 3
        + [_p("A", "f4", "MEDIUM")]
        + [_p("B", "f5", "HIGH")] * 2
        + [_p("B", "f5", "LOW")]
    )
    result = class_fid_min_severity(problems)
    assert result["A"]["f4"] == "MEDIUM", f"A/f4: min='MEDIUM'; got {result.get('A', {}).get('f4')}"
    assert result["B"]["f5"] == "LOW", f"B/f5: min='LOW'; got {result.get('B', {}).get('f5')}"
