"""older_than_predicate must compose under AND (act-probe oracle, 2026-09-21).

The helper returns ``A OR B``. A caller writing ``WHERE x = 1 AND {pred}`` gets
``(x = 1 AND A) OR B`` -- the OR escapes and B matches rows the caller excluded.
"""

from __future__ import annotations

from cohezion.core.event_log_reader import older_than_predicate


def _top_level_or_count(expr: str, at_depth: int = 0) -> int:
    depth = 0
    count = 0
    upper = expr.upper()
    for i, ch in enumerate(expr):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == at_depth and upper.startswith(" OR ", i):
            count += 1
    return count


def test_predicate_has_no_top_level_or() -> None:
    pred = older_than_predicate(7200, now=1_790_000_000.0)
    assert _top_level_or_count(pred) == 0, pred


def test_predicate_composes_with_and() -> None:
    pred = older_than_predicate(7200, now=1_790_000_000.0)
    assert _top_level_or_count(f"x = 1 AND {pred}") == 0


def test_both_branches_still_present() -> None:
    pred = older_than_predicate(7200, now=1_790_000_000.0)
    assert "type::is_number(timestamp) AND timestamp < 1789992800" in pred
    assert "type::is_datetime(timestamp) AND timestamp < time::now() - 7200s" in pred


def test_disjunction_is_preserved_inside_the_group() -> None:
    # Guards the degenerate "fix" of turning OR into AND (matches nothing): observed
    # from a local model on the first act-probe run, and it passed the checks above.
    pred = older_than_predicate(7200, now=1_790_000_000.0)
    assert _top_level_or_count(pred, at_depth=1) == 1, pred
