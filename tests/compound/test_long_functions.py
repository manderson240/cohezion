"""Discriminating tests for the long-function report (item 64, 2026-06-06).

`long_functions(paths, threshold=50)` flags functions whose SOURCE SPAN (`end_lineno - lineno + 1`)
exceeds `threshold` — the SIZE smell, distinct from CC's branchiness (a long function can be flat yet
hard to hold in the head). Span is hand-countable on a fixture, so the tests assert EXACT values.

Each test fails a plausible wrong impl:
  - off-by-one span (forgets the +1, or counts body-only) → test_span_is_exact_line_count,
  - wrong threshold boundary (>= vs >) → test_threshold_is_strict,
  - only reports top-level functions, missing nested defs → test_nested_def_is_its_own_entry,
  - crashes on a broken file → test_clean_and_badfile.
"""

from __future__ import annotations

import ast
from pathlib import Path

from cohezion.compound.simplicity_audit import _func_span, long_functions


def _span(src: str) -> int:
    fn = ast.parse(src).body[0]
    assert isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
    return _func_span(fn)


def test_span_is_exact_line_count() -> None:
    # def(1) + 3 body lines = 4 lines spanned (end_lineno - lineno + 1).
    assert _span("def f():\n    a = 1\n    b = 2\n    return a + b\n") == 4


def test_threshold_is_strict(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    # four(): 4 lines; five(): 5 lines. At threshold 4: five flagged (5>4), four NOT (4 not >4).
    f.write_text(
        "def four():\n    a = 1\n    b = 2\n    return a\n"
        "def five():\n    a = 1\n    b = 2\n    c = 3\n    return a\n"
    )
    out = long_functions([tmp_path], threshold=4)
    names = {n for n, _ in out}
    assert "m.py::five" in names
    assert "m.py::four" not in names  # span == threshold is NOT > threshold


def test_report_returns_exact_span(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text("def wide():\n    a = 1\n    b = 2\n    c = 3\n    return a\n")  # 5 lines
    assert long_functions([tmp_path], threshold=4) == [("m.py::wide", 5)]


def test_nested_def_is_its_own_entry(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    # outer spans the whole thing; inner is its own 3-line def — BOTH exceed threshold 2.
    f.write_text(
        "def outer():\n    def inner():\n        x = 1\n        return x\n    return inner()\n"
    )
    names = {n for n, _ in long_functions([tmp_path], threshold=2)}
    assert "m.py::outer" in names and "m.py::inner" in names  # nested def appears separately


def test_clean_and_badfile(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("def f():\n    return 1\n")  # 2 lines, under threshold
    (tmp_path / "broken.py").write_text("def f(:\n  oops\n")  # syntax error → skipped, no crash
    assert long_functions([tmp_path], threshold=50) == []
