"""Item 248: count_by_severity() — problem count per severity level (2026-06-08).

``count_by_severity(problems: list[Problem]) -> dict[str, int]``:
Returns ``{severity: count}`` for every non-empty severity value present
in the scan.  Problems with severity="" (default) are excluded from the
output dict.  Empty input → {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: problems with severity="" are NOT counted — their key
     does not appear in the output dict.
     Kills impl that includes all problems (even default severity="").
  2. Each entry equals the count of problems with that exact severity.
     Kills impl that de-duplicates finding_ids before counting.
  3. Empty input → {}.
     Kills impl that raises or returns None.
  4. Return type is dict[str, int] not dict[str, list].
     Kills impl returning filter_problems_by_severity groupings.
  5. Multiple severity levels all present with correct counts.
     Kills impl that only returns the most common severity.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_by_severity,
)


def _p(cls: str, severity: str = "", idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=severity)


def test_default_severity_excluded() -> None:
    """Problems with severity="" are excluded from the output dict.

    PRIMARY DISCRIMINATOR: kills impl that includes severity="" as a key.
    """
    problems = [_p("alpha", "", 0), _p("beta", "HIGH", 0)]

    result = count_by_severity(problems)

    assert "" not in result, (
        'severity="" must not appear in output; got ' + repr(result)
    )
    assert result.get("HIGH") == 1, "HIGH must have count=1; got " + repr(result)


def test_count_equals_number_of_matching_problems() -> None:
    """Each count equals the number of problems at that severity.

    Kills impl that counts unique finding_ids or classes.
    """
    problems = [
        _p("alpha", "HIGH", 0),
        _p("alpha", "HIGH", 1),
        _p("beta", "HIGH", 0),
        _p("gamma", "LOW", 0),
    ]

    result = count_by_severity(problems)

    assert result.get("HIGH") == 3, "HIGH has 3 problems; got " + repr(result)
    assert result.get("LOW") == 1, "LOW has 1 problem; got " + repr(result)


def test_empty_input_returns_empty_dict() -> None:
    """Empty input → {}.

    Kills impl that raises or returns None.
    """
    result = count_by_severity([])
    assert result == {}, "Empty input → {}; got " + repr(result)


def test_return_type_is_dict_of_int() -> None:
    """Return type is dict[str, int], not dict[str, list].

    Kills impl returning filter_problems_by_severity groupings.
    """
    result = count_by_severity([_p("alpha", "CRITICAL")])
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert isinstance(result.get("CRITICAL"), int), (
        "Values must be int; got " + repr(type(result.get("CRITICAL")))
    )


def test_multiple_severity_levels_all_present() -> None:
    """All non-empty severity levels appear in the output.

    Kills impl that only returns the most common severity.
    """
    problems = [
        _p("alpha", "HIGH", 0),
        _p("beta", "MEDIUM", 0),
        _p("gamma", "LOW", 0),
        _p("delta", "CRITICAL", 0),
    ]

    result = count_by_severity(problems)

    assert set(result.keys()) == {"HIGH", "MEDIUM", "LOW", "CRITICAL"}, (
        "All four severity levels must appear; got " + repr(result)
    )
