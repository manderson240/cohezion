"""Item 722: class_problem_count_by_severity_rank() -- rank-bucket histogram per class.

class_problem_count_by_severity_rank(problems) -> dict[str, dict[int, int]].
Returns {class: {0:count, 1:count, 2:count, 3:count, 4:count}} -- all 5 int-keyed
rank buckets ALWAYS present per class (missing ranks get 0).
CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1, INFO=0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: result[class] keyed by INT rank (not str severity label);
     class A: CRITICAL(4)+HIGH(3)+HIGH(3) -> {0:0, 1:0, 2:0, 3:2, 4:1};
     severity-keyed impl gives {'CRITICAL':1,'HIGH':2} wrong; count-only gives 3 wrong.
  2. All 5 rank keys present even when no problem maps to some ranks.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Unknown severity maps to rank 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_count_by_severity_rank


def _p(cls: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity=sev)


def test_int_rank_keys_not_str_labels_primary_discriminator() -> None:
    """PRIMARY DISC.: keys in inner dict are INT ranks, not str severity labels.

    class A: CRITICAL(4)+HIGH(3)+HIGH(3) -> {0:0, 1:0, 2:0, 3:2, 4:1}.
    severity-keyed impl gives {'CRITICAL':1,'HIGH':2} wrong type/key.
    count-only gives 3 wrong.
    """
    problems = [_p("A", "CRITICAL"), _p("A", "HIGH"), _p("A", "HIGH")]
    result = class_problem_count_by_severity_rank(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"'A' must be present; got {list(result)}"
    inner = result["A"]
    # Keys must be ints
    assert all(isinstance(k, int) for k in inner), (
        f"Inner keys must be int; got {[type(k) for k in inner]}"
    )
    assert inner[4] == 1, f"CRITICAL -> rank 4 count 1; got {inner.get(4)}"
    assert inner[3] == 2, f"HIGH*2 -> rank 3 count 2; got {inner.get(3)}"
    assert inner[2] == 0, f"No MEDIUM -> rank 2 count 0; got {inner.get(2)}"
    assert inner[1] == 0, f"No LOW -> rank 1 count 0; got {inner.get(1)}"
    assert inner[0] == 0, f"No INFO -> rank 0 count 0; got {inner.get(0)}"


def test_all_five_rank_keys_always_present() -> None:
    """All 5 rank keys present even when some are zero."""
    problems = [_p("B", "LOW")]
    result = class_problem_count_by_severity_rank(problems)
    inner = result["B"]
    assert set(inner.keys()) == {0, 1, 2, 3, 4}, (
        f"Must have all 5 int ranks; got {set(inner.keys())}"
    )
    assert inner[1] == 1, f"LOW -> rank 1; got {inner.get(1)}"
    assert inner[0] == 0 and inner[2] == 0 and inner[3] == 0 and inner[4] == 0


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_problem_count_by_severity_rank([]) == {}


def test_multiple_classes_independent() -> None:
    """Each class has its own rank histogram."""
    problems = [_p("X", "INFO"), _p("X", "INFO"), _p("X", "LOW")]   # X: rank0=2, rank1=1
    problems += [_p("Y", "CRITICAL"), _p("Y", "MEDIUM")]             # Y: rank4=1, rank2=1
    result = class_problem_count_by_severity_rank(problems)
    assert result["X"][0] == 2 and result["X"][1] == 1, f"X: rank0=2,rank1=1; got {result['X']}"
    assert result["Y"][4] == 1 and result["Y"][2] == 1, f"Y: rank4=1,rank2=1; got {result['Y']}"


def test_unknown_severity_maps_to_rank_zero() -> None:
    """Unknown severity -> rank 0 (same default as INFO)."""
    problems = [_p("Z", "UNKNOWN_LABEL")]
    result = class_problem_count_by_severity_rank(problems)
    assert result["Z"][0] == 1, f"Unknown -> rank 0; got {result['Z']}"
    assert sum(result["Z"].values()) == 1, "Total must equal 1 problem"
