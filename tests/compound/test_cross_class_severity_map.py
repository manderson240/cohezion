"""Item 254: cross_class_severity_map() — per-class severity breakdown (2026-06-08).

``cross_class_severity_map(problems: list[Problem]) -> dict[str, dict[str, int]]``:
Returns ``{class_name: {severity: count}}`` for all problems in the scan.
Unlabelled problems (``severity=""``) appear in the inner dict under key ``""``.
Empty input → ``{}``.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: each class maps to a {severity: count} inner dict.
     Kills impl mapping class → total count (flattened) instead of breakdown.
  2. Unlabelled problems (severity="") appear under severity key "" per class.
     Kills impl that excludes "" from the inner dict (analogous to count_by_severity).
  3. Counts equal the number of Problem instances at that class × severity pair.
     Kills impl returning unique finding_id sets instead of raw counts.
  4. Empty input → {}.
     Kills impl that raises on empty input.
  5. Return type is dict[str, dict[str, int]].
     Kills impl returning a flat dict or a list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    cross_class_severity_map,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_each_class_has_severity_breakdown() -> None:
    """Each class key maps to a {severity: count} dict, not a flat count.

    PRIMARY DISCRIMINATOR: kills impl that maps class → total_count without
    breaking down by severity (i.e. {class: int} instead of {class: {sev: int}}).
    alpha has 2 HIGH + 1 LOW; beta has 3 MEDIUM.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _ps("beta", 0, "MEDIUM"),
        _ps("beta", 1, "MEDIUM"),
        _ps("beta", 2, "MEDIUM"),
    ]
    result = cross_class_severity_map(problems)
    assert result["alpha"] == {"HIGH": 2, "LOW": 1}, "alpha: 2 HIGH + 1 LOW; got " + repr(
        result.get("alpha")
    )
    assert result["beta"] == {"MEDIUM": 3}, "beta: 3 MEDIUM; got " + repr(result.get("beta"))


def test_unlabelled_problems_under_empty_severity_key() -> None:
    """Problems with severity='' appear under key '' in each class's inner dict.

    Kills impl that skips unlabelled problems (analogous to count_by_severity
    which excludes '' — this function INCLUDES it).
    """
    problems = [
        Problem(problem_class="alpha", finding_id="alpha:0"),  # severity=""
        Problem(problem_class="alpha", finding_id="alpha:1"),  # severity=""
        _ps("alpha", 2, "HIGH"),
    ]
    result = cross_class_severity_map(problems)
    alpha = result["alpha"]
    assert "" in alpha, "Unlabelled problems must appear under '' key; got " + repr(alpha)
    assert alpha[""] == 2, "2 unlabelled → count=2; got " + repr(alpha.get(""))
    assert alpha["HIGH"] == 1, "1 HIGH; got " + repr(alpha.get("HIGH"))


def test_counts_equal_raw_problem_count() -> None:
    """Counts are raw problem counts, not unique class/finding_id set sizes.

    Kills impl that counts unique classes or finding_ids.
    Same class appears 3 times at HIGH — count must be 3.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(3)]
    result = cross_class_severity_map(problems)
    assert result["alpha"]["HIGH"] == 3, "3 HIGH problems → count=3; got " + repr(
        result.get("alpha")
    )


def test_empty_input_returns_empty_dict() -> None:
    """Empty input → {}.

    Kills impl that raises on empty input.
    """
    result = cross_class_severity_map([])
    assert result == {}, "Empty input → {}; got " + repr(result)


def test_return_type_is_nested_dict() -> None:
    """Return type is dict[str, dict[str, int]].

    Kills impl returning a flat dict or list.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = cross_class_severity_map(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for cls, breakdown in result.items():
        assert isinstance(cls, str), "Outer key must be str; got " + repr(type(cls))
        assert isinstance(breakdown, dict), "Inner value must be dict; got " + repr(type(breakdown))
        for sev, cnt in breakdown.items():
            assert isinstance(sev, str), "Inner key must be str"
            assert isinstance(cnt, int), "Count must be int"
