"""Item 223: problems_by_ratio_rank() — problems ranked by class pressure (2026-06-08).

``problems_by_ratio_rank(problems: list[Problem], thresholds: dict[str, int])``
-> ``list[Problem]``:
Returns Problems sorted by their class's ``count/threshold`` ratio descending;
within a class, original input order is preserved.  Zero-threshold and
unmonitored classes are placed LAST (lowest priority).  Pure; no I/O.

Useful for triage display: shows the most-pressured class's problems first::

    ranked = problems_by_ratio_rank(findings, limits)
    for p in ranked[:10]:  # top 10 highest-pressure problems
        show(p)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: problems of the highest-ratio class come first.
     Kills an impl that returns original input order or alphabetical class sort.
  2. Within a single class, original input order is preserved.
     Kills an impl that sorts within-class by finding_id or class name.
  3. Unmonitored classes placed last.
     Kills an impl that interleaves unmonitored with monitored classes.
  4. Empty problems -> []; empty thresholds preserves order (all unmonitored, last).
     Kills an impl that raises on degenerate inputs.
  5. Return type is list[Problem] (same objects, reordered).
     Kills an impl that returns class names or finding_ids instead of Problems.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_by_ratio_rank,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_highest_ratio_class_first() -> None:
    """Problems of the highest-ratio class appear first.

    PRIMARY DISCRIMINATOR: kills an impl returning original input order.
    beta: 3 findings / threshold=3 = ratio 1.0
    alpha: 1 finding / threshold=10 = ratio 0.1
    -> beta's problems must appear before alpha's.
    """
    p_alpha = _p("alpha", "alpha:0")
    p_beta0 = _p("beta", "beta:0")
    p_beta1 = _p("beta", "beta:1")
    p_beta2 = _p("beta", "beta:2")
    problems = [p_alpha, p_beta0, p_beta1, p_beta2]
    thresholds = {"alpha": 10, "beta": 3}

    result = problems_by_ratio_rank(problems, thresholds)

    assert result[0].problem_class == "beta", (
        "beta (ratio=1.0) problems must come first; got " + repr([p.problem_class for p in result])
    )
    assert result[-1].problem_class == "alpha", "alpha (ratio=0.1) must be last; got " + repr(
        [p.problem_class for p in result]
    )


def test_within_class_input_order_preserved() -> None:
    """Within the same class, original input order is preserved.

    Kills an impl that sorts by finding_id within a class.
    """
    p1 = _p("alpha", "alpha:second")  # originally first
    p2 = _p("alpha", "alpha:first")  # originally second (id sorts earlier but input order later)
    problems = [p1, p2]
    thresholds = {"alpha": 5}

    result = problems_by_ratio_rank(problems, thresholds)

    alpha_problems = [p for p in result if p.problem_class == "alpha"]
    assert alpha_problems == [p1, p2], "Within-class order must match input; got " + repr(
        [p.finding_id for p in alpha_problems]
    )


def test_unmonitored_class_placed_last() -> None:
    """Problems from unmonitored classes appear after all monitored classes.

    Kills an impl that interleaves unmonitored with monitored.
    """
    p_unmonitored = _p("unknown", "unknown:0")
    p_monitored = _p("alpha", "alpha:0")
    problems = [p_unmonitored, p_monitored]
    thresholds = {"alpha": 5}  # "unknown" not in thresholds

    result = problems_by_ratio_rank(problems, thresholds)

    assert result[-1].problem_class == "unknown", "Unmonitored class must be last; got " + repr(
        [p.problem_class for p in result]
    )
    assert result[0].problem_class == "alpha", "Monitored class must come first; got " + repr(
        [p.problem_class for p in result]
    )


def test_empty_inputs_return_empty_or_identity() -> None:
    """Degenerate inputs: empty problems -> []; any problems + empty thresholds -> all last."""
    assert problems_by_ratio_rank([], {"alpha": 5}) == [], "Empty problems must return []"

    p = _p("alpha", "alpha:0")
    result = problems_by_ratio_rank([p], {})
    assert result == [p], "Empty thresholds: problem placed last (only element) -> [p]"


def test_return_type_is_list_of_problem() -> None:
    """Return value is list[Problem] containing the original Problem objects (reordered).

    Kills an impl that returns class names or finding_ids.
    """
    p = _p("alpha", "alpha:0")
    result = problems_by_ratio_rank([p], {"alpha": 3})
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 1
    assert result[0] is p, "Must return original Problem objects; got " + repr(result[0])
