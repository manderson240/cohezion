"""Discriminating tests for max-nesting-depth outliers (item 47, 2026-06-06).

`nesting_outliers(paths, *, threshold=5)` reports the deepest block-nesting (if/for/while/with/try)
per function — the "arrow anti-pattern" (DEPTH), the complement to item-43's cyclomatic complexity
(BREADTH: how MANY branches). Report-only.

Each test fails a plausible wrong impl:
  - off-by-one or wrong depth → test_depth_equals_nesting (hand-computed K),
  - a nested def's deep body inflates the ENCLOSING function → test_nested_def_does_not_inflate,
  - threshold not strict → test_threshold_is_exact,
  - flat function flagged → test_flat_not_flagged.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import nesting_outliers


# 6 nested if-blocks → depth 6 (hand-computable).
_DEEP = """\
def deep(a, b, c, d, e, f):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            return 1
    return 0


def flat(x):
    y = x + 1
    return y
"""

# outer nests only 1 block but contains a deeply-nested NESTED def (depth 6 on its own).
_NESTED_DEF = """\
def outer(a):
    if a:
        def inner(b, c, d, e, f, g):
            if b:
                if c:
                    if d:
                        if e:
                            if f:
                                if g:
                                    return 1
        return inner
    return None
"""


def _names(rows: list[tuple[str, int]]) -> dict[str, int]:
    return {q.split("::")[-1]: depth for q, depth in rows}


def test_depth_equals_nesting(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(_DEEP)
    rows = _names(nesting_outliers([tmp_path], threshold=5))
    assert rows.get("deep") == 6, "6 nested if-blocks → depth 6"


def test_flat_not_flagged(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(_DEEP)
    rows = _names(nesting_outliers([tmp_path], threshold=5))
    assert "flat" not in rows  # depth 0 → not over threshold


def test_nested_def_does_not_inflate(tmp_path: Path) -> None:
    f = tmp_path / "n.py"
    f.write_text(_NESTED_DEF)
    rows = _names(nesting_outliers([tmp_path], threshold=5))
    assert "outer" not in rows, "outer's OWN depth is 1 — the nested def must not inflate it"
    assert rows.get("inner") == 6, "the nested def is scored separately, depth 6"


def test_threshold_is_exact(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(_DEEP)
    # threshold=6 → depth-6 'deep' is NOT > 6 → absent (strict).
    assert "deep" not in _names(nesting_outliers([tmp_path], threshold=6))
    # threshold=5 → depth 6 > 5 → present.
    assert "deep" in _names(nesting_outliers([tmp_path], threshold=5))


def test_clean_tree_empty(tmp_path: Path) -> None:
    (tmp_path / "c.py").write_text("def g(x):\n    if x:\n        return 1\n    return 0\n")
    assert nesting_outliers([tmp_path], threshold=5) == []
