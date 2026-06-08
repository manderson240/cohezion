"""Item 313: problems_by_finding_id() — group Problem records by finding_id (2026-06-08).

``problems_by_finding_id(problems) -> dict[str, list[Problem]]``:
Returns a dict mapping each finding_id to the list of Problem records that share it.
Records preserve input order within each group.  ALL records included regardless of
severity label (labelled and unlabelled).  Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: records are in INPUT ORDER, not sorted by any field.
     Kills impl that sorts records within each group.
  2. ALL records included regardless of severity (unlabelled included too).
     Kills impl that filters out unlabelled (severity='') records.
  3. Empty input -> {}.
     Kills impl that crashes or returns non-empty.
  4. Single record -> {finding_id: [record]}.
     Kills impl that requires multiple records per group.
  5. Return type is dict[str, list[Problem]]; each list element is a Problem.
     Kills impl returning wrong collection types.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_by_finding_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_records_in_input_order_not_sorted() -> None:
    """Records within each group preserve input order (not sorted by any field).

    PRIMARY DISCRIMINATOR: kills impl sorting records.
    f001: inserted as LOW then CRITICAL -> result list must be [LOW, CRITICAL].
    """
    p_low = _p("alpha", "f001", "LOW")
    p_crit = _p("alpha", "f001", "CRITICAL")
    problems = [p_low, p_crit]
    result = problems_by_finding_id(problems)
    assert "f001" in result, "f001 in result; got keys: " + repr(list(result.keys()))
    assert result["f001"] == [p_low, p_crit], (
        "Order must be input order (LOW then CRITICAL); got " + repr(result["f001"])
    )


def test_unlabelled_records_included() -> None:
    """ALL records included regardless of severity; unlabelled not filtered out.

    Kills impl that filters records with severity=''.
    f002: 1 unlabelled + 1 HIGH -> both in list.
    """
    p_unlabelled = _p("beta", "f002")       # severity=''
    p_high = _p("beta", "f002", "HIGH")
    problems = [p_unlabelled, p_high]
    result = problems_by_finding_id(problems)
    assert "f002" in result, "f002 in result; got keys: " + repr(list(result.keys()))
    assert len(result["f002"]) == 2, (
        "Both records (unlabelled + HIGH) in list; got " + repr(result["f002"])
    )
    assert p_unlabelled in result["f002"], "unlabelled record included; got " + repr(result["f002"])


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {}.

    Kills impl that crashes or returns non-empty.
    """
    result = problems_by_finding_id([])
    assert result == {}, "empty -> {}; got " + repr(result)


def test_single_record_produces_single_element_list() -> None:
    """Single record -> {finding_id: [record]}.

    Kills impl that requires multiple records per group.
    """
    p = _p("gamma", "f003", "MEDIUM")
    result = problems_by_finding_id([p])
    assert result == {"f003": [p]}, (
        "Single record -> {f003: [record]}; got " + repr(result)
    )


def test_return_type_is_dict_of_lists_of_problems() -> None:
    """Return type is dict[str, list[Problem]]; elements are Problem instances.

    Kills impl returning wrong collection types.
    """
    p = _p("delta_cls", "f004", "HIGH")
    result = problems_by_finding_id([p])
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    group = result.get("f004")
    assert isinstance(group, list), "Group must be list; got " + repr(type(group))
    assert isinstance(group[0], Problem), (
        "Elements must be Problem; got " + repr(type(group[0]))
    )
