"""Item 188: exclude_problems() — post-hoc ID exclusion utility (2026-06-08).

``exclude_problems(problems: list[Problem], exclude_ids: frozenset[str])``
→ ``list[Problem]``:
Returns a new list with all findings whose ``finding_id`` is in *exclude_ids*
removed.  Empty *exclude_ids* → list returned unchanged.  Pure; no I/O.

Post-hoc counterpart to the ``exclude_known`` parameter in
:func:`discover_problems`.  Enables::

    novel = exclude_problems(all_findings, previously_actioned_ids)

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: list with a matching finding → that finding removed.
     Kills a no-op impl that returns all findings unchanged.
  2. Empty *exclude_ids* → all findings returned unchanged.
     Kills an impl that always removes the first finding regardless of exclude_ids.
  3. Empty *problems* → [] (no raises).
     Kills an impl that raises IndexError on empty input.
  4. Non-matching *exclude_ids* → list unchanged.
     Kills an impl that removes findings by index instead of by ID.
  5. Multiple matches → all removed in one call.
     Kills an impl that removes only the first matching finding.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    exclude_problems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_matching_finding_removed() -> None:
    """Finding whose ID is in exclude_ids is removed from the result.

    PRIMARY DISCRIMINATOR: kills a no-op impl that returns all findings
    unchanged (ignoring the exclude_ids argument).
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("long_function")]
    exclude_ids = frozenset({"nesting_outlier:0"})

    result = exclude_problems(problems, exclude_ids)

    fids = {p.finding_id for p in result}
    assert "nesting_outlier:0" not in fids, f"Excluded ID must be absent from result; got {fids!r}"
    assert len(result) == 2, f"One finding removed → length 2; got {len(result)}: {result!r}"


def test_empty_exclude_ids_returns_all() -> None:
    """Empty *exclude_ids* → all findings returned unchanged.

    Kills an impl that always removes the first finding regardless of
    what exclude_ids contains.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = exclude_problems(problems, frozenset())

    assert len(result) == 2, (
        f"Empty exclude_ids must return all findings; got {len(result)}: {result!r}"
    )


def test_empty_problems_returns_empty() -> None:
    """Empty *problems* → [] (no raises).

    Kills an impl that raises IndexError on empty input.
    """
    result = exclude_problems([], frozenset({"complexity_outlier:0"}))

    assert result == [], f"Empty problems must return []; got {result!r}"


def test_non_matching_exclude_ids_unchanged() -> None:
    """*exclude_ids* with no matching finding → list returned unchanged.

    Kills an impl that removes findings by index rather than by ID, which
    would incorrectly remove findings even when nothing matches.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]
    exclude_ids = frozenset({"long_function:0", "compound_smell:5"})  # neither in problems

    result = exclude_problems(problems, exclude_ids)

    assert len(result) == 2, (
        f"No-match exclude_ids must return all findings; got {len(result)}: {result!r}"
    )


def test_multiple_matches_all_removed() -> None:
    """Multiple findings matching exclude_ids → all removed in one call.

    Kills an impl that removes only the FIRST matching finding and
    leaves subsequent matches in the result.
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
    ]
    exclude_ids = frozenset({"complexity_outlier:0", "complexity_outlier:1"})

    result = exclude_problems(problems, exclude_ids)

    assert len(result) == 1, (
        f"Both complexity_outlier findings must be removed; got {len(result)}: {result!r}"
    )
    assert result[0].finding_id == "nesting_outlier:0", (
        f"Only nesting_outlier must remain; got {result[0].finding_id!r}"
    )
