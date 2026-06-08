"""Item 616: fid_severity_distinct_count() -- distinct severity labels per fid.

``fid_severity_distinct_count(problems) -> dict[str, int]``:
Returns {fid: distinct_sev_count} -- cardinality of the severity label set.
FID-axis complement of class_severity_distinct_count.
Unlabelled (empty severity) excluded from count.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid (not class); counts DISTINCT labels (not total count).
     fid 'f1' HIGH=3, LOW=2 -> result['f1']==2 distinct (not 5=total, not result['A']).
     Kills impl on wrong axis or returning total count.
  2. Unlabelled excluded from distinct count.
     fid 'f2' HIGH=2, unlabelled=3 -> distinct_count=1 (only HIGH is labelled).
     Kills impl counting unlabelled as a severity label.
  3. Single-severity per fid -> distinct=1.
     Kills impl returning 0 for a single bucket.
  4. Empty -> {}.
  5. All-same label across many problems -> distinct=1.
     Kills impl returning the problem count instead of label count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_severity_distinct_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_distinct_labels_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, counts DISTINCT labels not total count.

    fid 'f1' HIGH=3, LOW=2 -> distinct=2 (not total=5, not class='A').
    Kills class-axis impl and total-counting impl.
    """
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("B", "f1", "LOW")] * 2
    result = fid_severity_distinct_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"Class 'A' must NOT be key; got {result}"
    assert result["f1"] == 2, (
        f"HIGH=3, LOW=2: distinct=2 labels; got {result['f1']} "
        f"(5=total count wrong, 'A'=wrong axis)"
    )


def test_unlabelled_excluded_from_distinct_count() -> None:
    """Unlabelled severity not counted as a distinct label.

    fid 'f2' HIGH=2, unlabelled=3 -> distinct=1 (only HIGH is a real label).
    Kills impl treating empty string as a severity label.
    """
    problems = [_p("A", "f2", "HIGH")] * 2 + [_p("A", "f2", "")]  * 3
    result = fid_severity_distinct_count(problems)
    assert result["f2"] == 1, (
        f"HIGH=2 + 3 unlabelled: distinct=1; got {result['f2']} "
        f"(2=wrong if including unlabelled)"
    )


def test_single_severity_returns_one() -> None:
    """Single labelled severity per fid -> distinct=1.

    Kills impl returning 0.
    """
    problems = [_p("A", "fy", "CRITICAL")] * 4
    result = fid_severity_distinct_count(problems)
    assert result["fy"] == 1, f"CRITICAL x4 -> distinct=1; got {result['fy']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_distinct_count([]) == {}


def test_all_same_label_returns_one() -> None:
    """All HIGH -> distinct=1 (not the problem count).

    fid 'fx' HIGH x7 -> distinct=1.
    Kills impl returning 7 (total) instead of 1 (distinct).
    """
    problems = [_p("A", "fx", "HIGH")] * 7
    result = fid_severity_distinct_count(problems)
    assert result["fx"] == 1, f"7 HIGH -> distinct=1; got {result['fx']}"
