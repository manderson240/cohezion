"""Item 756: fid_severity_rank_unique_count() -- distinct severity rank count per fid.

fid_severity_rank_unique_count(problems) -> dict[str, int].
Fid-axis complement of class_severity_rank_unique_count (item 755).
Count of distinct _SEVERITY_RANK values per fid.
All-same -> 1.  Empty -> {}.  Returns int.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: outer key is FID AND unique not total; fid f1: INFO*3+HIGH*2
     -> unique=2; class-outer gives 'A' wrong; total-count gives 5 wrong.
  2. All-same -> 1.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_rank_unique_count


def _p(fid: str, sev: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity=sev)


def test_fid_outer_unique_primary_discriminator() -> None:
    """PRIMARY DISC.: outer key is FID; unique=2; total-count gives 5 wrong.

    fid f1: INFO(0)*3+HIGH(3)*2 -> 2 distinct ranks.
    """
    problems = [
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "INFO"),
        _p("f1", "HIGH"),
        _p("f1", "HIGH"),
    ]
    result = fid_severity_rank_unique_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"'f1' must be outer key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {list(result)}"
    got = result["f1"]
    assert got == 2, f"INFO*3+HIGH*2 -> 2 distinct; got {got}"
    assert got != 5, "Must be unique not total"


def test_all_same_gives_one() -> None:
    """All same -> unique_count = 1."""
    problems = [_p("f2", "CRITICAL")] * 4
    result = fid_severity_rank_unique_count(problems)
    assert result.get("f2") == 1, f"All CRITICAL -> 1; got {result.get('f2')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_rank_unique_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Two fids computed independently."""
    problems = [
        _p("fA", "INFO"),
        _p("fA", "HIGH"),
        _p("fA", "CRITICAL"),  # unique=3
        _p("fB", "LOW"),
        _p("fB", "LOW"),  # unique=1
    ]
    result = fid_severity_rank_unique_count(problems)
    assert result["fA"] == 3, f"fA -> 3; got {result['fA']}"
    assert result["fB"] == 1, f"fB -> 1; got {result['fB']}"


def test_return_type_is_int() -> None:
    """Result values must be int."""
    problems = [_p("f3", "INFO"), _p("f3", "HIGH")]
    result = fid_severity_rank_unique_count(problems)
    assert isinstance(result["f3"], int), f"Must be int; got {type(result['f3'])}"
