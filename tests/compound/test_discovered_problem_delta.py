"""Item 127: discovered_problem_delta — TDD red→green (2026-06-08).

``discovered_problem_delta(before, after)`` over two ``list[Problem]`` returns
``{resolved, introduced}``:
  - ``resolved``: in ``before`` but NOT ``after`` (fixed since last scan)
  - ``introduced``: in ``after`` but NOT ``before`` (new debt)

A problem in BOTH → in neither list (kills an impl reporting common problems).
Compared by ``finding_id`` (the stable TIDE identity key).

Mirrors the harness-blessed ``DegradationDetector.diff_snapshots`` (CB11) +
item-39/57/74/81 pure-delta family.

Discriminating tests — each kills a plausible wrong implementation:

  1. Before-only → resolved; after-only → introduced   (PRIMARY DISC.: kills "resolved=before")
  2. In BOTH → neither list                            (kills "resolved=set(before)")
  3. Identical scans → both empty                      (kills impl that reports common items)
  4. Empty inputs → both empty                         (kills impl that raises)
  5. Keyed by finding_id, not problem_class            (kills "dedupe by class")
"""

from __future__ import annotations

from cohezion.compound.problem_delta import discovered_problem_delta
from cohezion.compound.problem_discovery import Problem


def _p(finding_id: str, problem_class: str = "complexity") -> Problem:
    return Problem(problem_class=problem_class, finding_id=finding_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_before_only_resolved_after_only_introduced() -> None:
    """A problem in before but not after → resolved; in after but not before → introduced.

    PRIMARY DISCRIMINATOR: kills an impl that returns ``resolved=set(before)``
    (which would also include the shared problem) or ``introduced=set(after)``.
    """
    before = [_p("foo"), _p("bar")]
    after = [_p("bar"), _p("baz")]
    delta = discovered_problem_delta(before, after)
    assert _p("foo") in delta.resolved, f"foo (before-only) must be resolved; got {delta}"
    assert _p("baz") in delta.introduced, f"baz (after-only) must be introduced; got {delta}"


def test_common_problem_in_neither_list() -> None:
    """A problem in BOTH before AND after → in neither resolved nor introduced.

    Kills an impl that reports every problem in before as resolved.
    """
    shared = _p("bar")
    before = [_p("foo"), shared]
    after = [shared, _p("baz")]
    delta = discovered_problem_delta(before, after)
    assert shared not in delta.resolved, f"shared must NOT be resolved; got {delta}"
    assert shared not in delta.introduced, f"shared must NOT be introduced; got {delta}"


def test_identical_scans_both_empty() -> None:
    """Identical before and after → both resolved and introduced are empty.

    Kills an impl that re-reports the full list as resolved+introduced.
    """
    problems = [_p("foo"), _p("bar")]
    delta = discovered_problem_delta(problems, problems)
    assert delta.resolved == [], f"identical scans → resolved must be []; got {delta.resolved}"
    assert delta.introduced == [], (
        f"identical scans → introduced must be []; got {delta.introduced}"
    )


def test_empty_inputs_both_empty() -> None:
    """Both empty → both resolved and introduced are empty (no crash).

    Kills an impl that raises on empty inputs.
    """
    delta = discovered_problem_delta([], [])
    assert delta.resolved == []
    assert delta.introduced == []


def test_keyed_by_finding_id_not_class() -> None:
    """Delta comparison uses finding_id, not problem_class.

    Kills an impl that deduplicates by problem_class alone: two findings
    with the same problem_class but DIFFERENT finding_ids are distinct.
    """
    # Same problem_class, different finding_ids → both track independently.
    before = [Problem(problem_class="complexity", finding_id="foo")]
    after = [Problem(problem_class="complexity", finding_id="bar")]
    delta = discovered_problem_delta(before, after)
    # foo resolved, bar introduced — if keyed by class alone, both would be missing
    resolved_ids = {p.finding_id for p in delta.resolved}
    introduced_ids = {p.finding_id for p in delta.introduced}
    assert "foo" in resolved_ids, f"foo must be resolved; got {delta}"
    assert "bar" in introduced_ids, f"bar must be introduced; got {delta}"
