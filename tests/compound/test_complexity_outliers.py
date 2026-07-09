"""Discriminating tests for the cyclomatic-complexity outlier report (item 43, 2026-06-06).

`complexity_outliers(paths, threshold)` flags functions whose McCabe cyclomatic complexity
exceeds `threshold`. CC is hand-computable on a fixture, so the tests assert EXACT values.

Each test fails a plausible wrong impl:
  - off-by-one base (start at 0, or count the function node) → T_flat / T_branches,
  - count nested-def branches against the enclosing function → T_nested,
  - wrong threshold boundary (>= vs >) → T_threshold,
  - crash on a syntactically-broken file → T_badfile.
"""

from __future__ import annotations

import ast
from pathlib import Path

from cohezion.compound.simplicity_audit import _cyclomatic_complexity, complexity_outliers


def _cc(src: str) -> int:
    fn = ast.parse(src).body[0]
    assert isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
    return _cyclomatic_complexity(fn)


def test_flat_function_has_cc_1() -> None:
    assert _cc("def f(x):\n    return x + 1\n") == 1


def test_each_decision_point_adds_one() -> None:
    # 2 ifs + 1 for + 1 while = 4 decision points → CC = 5.
    src = (
        "def f(xs):\n"
        "    total = 0\n"
        "    for x in xs:\n"
        "        if x > 0:\n"
        "            total += x\n"
        "        if x < 0:\n"
        "            total -= x\n"
        "    while total > 100:\n"
        "        total -= 1\n"
        "    return total\n"
    )
    assert _cc(src) == 5


def test_boolean_operators_and_ternary_and_comprehension_if() -> None:
    # `a and b and c` → 2 ops; one ternary → +1; comprehension with one `if` → +1. Base 1 → CC 5.
    src = (
        "def f(a, b, c, xs):\n"
        "    flag = a and b and c\n"  # +2
        "    y = 1 if flag else 2\n"  # +1 (IfExp)
        "    z = [v for v in xs if v]\n"  # +1 (comprehension if)
        "    return y + z[0]\n"
    )
    assert _cc(src) == 5


def test_nested_def_branches_do_not_inflate_enclosing() -> None:
    # The enclosing f has ONE if (CC 2); the nested g's two ifs must NOT count toward f.
    src = (
        "def f(x):\n"
        "    def g(y):\n"
        "        if y > 0:\n"
        "            return 1\n"
        "        if y < 0:\n"
        "            return -1\n"
        "        return 0\n"
        "    if x:\n"
        "        return g(x)\n"
        "    return 0\n"
    )
    assert _cc(src) == 2


def test_outliers_filter_strictly_above_threshold(tmp_path: Path) -> None:
    # A function with exactly 3 ifs → CC 4. threshold=4 → excluded (strict >); threshold=3 → included.
    f = tmp_path / "m.py"
    f.write_text(
        "def busy(x):\n"
        "    if x == 1:\n        return 1\n"
        "    if x == 2:\n        return 2\n"
        "    if x == 3:\n        return 3\n"
        "    return 0\n"
    )
    assert complexity_outliers([f], threshold=4) == []  # CC 4 is NOT > 4
    assert complexity_outliers([f], threshold=3) == [("m.py::busy", 4)]


def test_broken_file_is_skipped_not_crashed(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("def a(x):\n" + "    if x: pass\n" * 20 + "    return x\n")
    (tmp_path / "broken.py").write_text("def (((:\n")  # SyntaxError
    out = complexity_outliers([tmp_path], threshold=10)
    assert out == [("ok.py::a", 21)]  # ok.py scored (CC 21), broken.py skipped without crashing
