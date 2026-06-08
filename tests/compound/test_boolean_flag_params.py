"""Discriminating tests for the boolean-flag-argument report (item 97, 2026-06-07).

`boolean_flag_params(paths, threshold=2)` flags functions with `>= threshold` parameters whose
DEFAULT is a boolean literal (`True`/`False`) — the "flag argument / this function secretly does N
things" CONTROL-COUPLING smell, distinct from the raw param count of `long_parameter_lists` (item
63) and the size of `long_functions` (item 64). Boolean-default count is hand-computable on a
fixture, so the tests assert EXACT values.

Each test fails a plausible wrong impl:
  - counts ANY default, not just booleans → test_non_boolean_defaults_not_counted,
  - counts `1`/`0` as booleans (bool is an int subclass) → test_int_literal_is_not_boolean,
  - misses keyword-only boolean defaults → test_kwonly_boolean_defaults_counted,
  - counts params that have no default → test_param_without_default_not_counted,
  - wrong threshold boundary (`>` instead of `>=`) → test_threshold_is_inclusive,
  - crashes on a broken file → test_clean_and_badfile_skipped.
"""

from __future__ import annotations

import ast
from pathlib import Path

from cohezion.compound.simplicity_audit import _boolean_default_count, boolean_flag_params


def _bdc(src: str) -> int:
    fn = ast.parse(src).body[0]
    assert isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
    return _boolean_default_count(fn)


def test_two_boolean_defaults_counted() -> None:
    assert _bdc("def f(a=True, b=False):\n    return 0\n") == 2


def test_one_boolean_default_counted() -> None:
    assert _bdc("def f(a, b=True):\n    return 0\n") == 1


def test_param_without_default_not_counted() -> None:
    # positional params with no default are not flags (nothing to branch on)
    assert _bdc("def f(a, b, c):\n    return 0\n") == 0


def test_non_boolean_defaults_not_counted() -> None:
    # 0, "", None are defaults but NOT boolean literals → not flag arguments
    assert _bdc("def f(a=0, b='', c=None):\n    return 0\n") == 0


def test_int_literal_is_not_boolean() -> None:
    # the bool-is-int-subclass trap: `1` must NOT count, only the real `True` does
    assert _bdc("def f(a=1, b=True):\n    return 0\n") == 1


def test_kwonly_boolean_defaults_counted() -> None:
    # keyword-only params with bool defaults count too (args.kw_defaults)
    assert _bdc("def f(a, *, verbose=True, dry_run=False):\n    return 0\n") == 2


def test_kwonly_without_default_not_counted() -> None:
    # a kw-only param with no default has a Python None placeholder in kw_defaults → skipped
    assert _bdc("def f(a, *, k, verbose=True):\n    return 0\n") == 1


def test_threshold_is_inclusive(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "def one(a=True):\n    return 0\n"  # 1 bool default → NOT flagged at threshold 2
        "def two(a=True, b=False):\n    return 0\n"  # 2 → flagged (>= threshold)
    )
    out = boolean_flag_params([tmp_path], threshold=2)
    names = [n for n, _ in out]
    assert any("two" in n for n in names)
    assert not any("one" in n for n in names)  # count == threshold IS flagged (>=), count < is not


def test_report_returns_exact_count(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text("def cfg(self, a=True, b=False, c=True, d=0):\n    return 0\n")  # 3 bool defaults
    out = boolean_flag_params([tmp_path], threshold=2)
    assert out == [("m.py::cfg", 3)]


def test_sorted_by_count_descending(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "def lo(a=True, b=True):\n    return 0\n"  # 2
        "def hi(a=True, b=False, c=True):\n    return 0\n"  # 3 → first
    )
    out = boolean_flag_params([tmp_path], threshold=2)
    assert out == [("m.py::hi", 3), ("m.py::lo", 2)]


def test_clean_and_badfile_skipped(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("def f(a, b=0):\n    return 0\n")  # no bool defaults
    (tmp_path / "broken.py").write_text("def f(:\n  oops\n")  # syntax error → skipped, no crash
    assert boolean_flag_params([tmp_path], threshold=2) == []
