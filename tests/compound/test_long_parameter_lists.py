"""Discriminating tests for the long-parameter-list report (item 63, 2026-06-06).

`long_parameter_lists(paths, threshold=6)` flags functions whose parameter count exceeds `threshold`
— the "too many arguments / data clump" smell, a structural-cost dimension distinct from CC/nesting.
`self`/`cls` are excluded; `*args`/`**kwargs` each count as one. Param count is hand-computable on a
fixture, so the tests assert EXACT values.

Each test fails a plausible wrong impl:
  - counts the leading self/cls → test_self_cls_excluded,
  - ignores *args/**kwargs (or counts each as 0/2) → test_varargs_kwargs_each_count_one,
  - wrong threshold boundary (>= vs >) → test_threshold_is_strict,
  - misses kw-only/pos-only params → test_all_param_kinds_counted,
  - crashes on a broken file → test_badfile_skipped.
"""

from __future__ import annotations

import ast
from pathlib import Path

from cohezion.compound.simplicity_audit import _param_count, long_parameter_lists


def _pc(src: str) -> int:
    fn = ast.parse(src).body[0]
    assert isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
    return _param_count(fn)


def test_plain_params_counted() -> None:
    assert _pc("def f(a, b, c):\n    return 0\n") == 3


def test_self_cls_excluded() -> None:
    assert _pc("def m(self, a, b):\n    return 0\n") == 2  # self not counted
    assert _pc("def c(cls, a):\n    return 0\n") == 1  # cls not counted
    # a non-method 'self'-less function with a param literally named 'self' is an edge — leading
    # self is excluded by name regardless, which is the documented rule.


def test_varargs_kwargs_each_count_one() -> None:
    assert _pc("def f(a, *args, **kwargs):\n    return 0\n") == 3  # a + *args + **kwargs


def test_all_param_kinds_counted() -> None:
    # 1 pos-only + 1 normal + 1 kw-only + *args + **kwargs = 5
    assert _pc("def f(p, /, a, *args, k, **kwargs):\n    return 0\n") == 5


def test_threshold_is_strict(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "def six(a, b, c, d, e, f):\n    return 0\n"  # exactly 6 → NOT flagged at threshold 6
        "def seven(a, b, c, d, e, f, g):\n    return 0\n"  # 7 → flagged
    )
    out = long_parameter_lists([tmp_path], threshold=6)
    names = [n for n, _ in out]
    assert any("seven" in n for n in names)
    assert not any("six" in n for n in names)  # K == threshold is NOT > threshold


def test_report_returns_exact_count(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text("def wide(self, a, b, c, d, e, f, g):\n    return 0\n")  # self excluded → 7
    out = long_parameter_lists([tmp_path], threshold=6)
    assert out == [("m.py::wide", 7)]


def test_clean_and_badfile_skipped(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("def f(a, b):\n    return 0\n")
    (tmp_path / "broken.py").write_text("def f(:\n  oops\n")  # syntax error → skipped, no crash
    assert long_parameter_lists([tmp_path], threshold=6) == []
