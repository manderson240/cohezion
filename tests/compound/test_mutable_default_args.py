"""Discriminating tests for the mutable-default-argument report (item 110, 2026-06-07).

`mutable_default_args(paths)` flags functions with a parameter whose DEFAULT is a mutable literal
— a list/dict/set display (`[]`, `{}`, `{1}`) or a `list()`/`dict()`/`set()` call — the classic
Python shared-mutable-default footgun (the default object is created ONCE and persists across
calls). Extends item-97's default-inspection thread from control-coupling to a CORRECTNESS smell.

Each test fails a plausible wrong impl:
  - flags ANY default, not just mutable ones → test_immutable_defaults_not_flagged,
  - conflates the immutable tuple `()` with a mutable `[]` → test_empty_tuple_not_flagged,
  - misses the `list()`/`dict()`/`set()` call form → test_constructor_call_defaults_flagged,
  - flags `frozenset()` (immutable) as a set → test_frozenset_not_flagged,
  - flags params that have no default → test_param_without_default_not_flagged,
  - crashes on a broken file → test_clean_and_badfile_skipped.
"""

from __future__ import annotations

import ast
from pathlib import Path

from cohezion.compound.simplicity_audit import _mutable_default_count, mutable_default_args


def _mdc(src: str) -> int:
    fn = ast.parse(src).body[0]
    assert isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
    return _mutable_default_count(fn)


def test_list_display_default_flagged() -> None:
    assert _mdc("def f(x=[]):\n    return 0\n") == 1


def test_dict_and_set_display_defaults_flagged() -> None:
    assert _mdc("def f(a={}, b={1}):\n    return 0\n") == 2  # empty dict + non-empty set


def test_constructor_call_defaults_flagged() -> None:
    assert _mdc("def f(a=list(), b=dict(), c=set()):\n    return 0\n") == 3


def test_immutable_defaults_not_flagged() -> None:
    # 0, "", None, True are immutable literals → not the footgun
    assert _mdc("def f(a=0, b='', c=None, d=True):\n    return 0\n") == 0


def test_empty_tuple_not_flagged() -> None:
    # () is an IMMUTABLE tuple, not a mutable list — must not be conflated with []
    assert _mdc("def f(a=(), b=(1, 2)):\n    return 0\n") == 0


def test_frozenset_not_flagged() -> None:
    # frozenset() is immutable; only list/dict/set constructors are the footgun
    assert _mdc("def f(a=frozenset(), b=tuple()):\n    return 0\n") == 0


def test_param_without_default_not_flagged() -> None:
    assert _mdc("def f(a, b, c):\n    return 0\n") == 0


def test_kwonly_mutable_default_flagged() -> None:
    assert _mdc("def f(a, *, opts=[]):\n    return 0\n") == 1


def test_report_returns_exact_count(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text("def bad(self, a=[], b={}, c=0):\n    return 0\n")  # 2 mutable defaults
    out = mutable_default_args([tmp_path])
    assert out == [("m.py::bad", 2)]


def test_clean_and_badfile_skipped(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("def f(a, b=None):\n    return 0\n")  # immutable default
    (tmp_path / "broken.py").write_text("def f(:\n  oops\n")  # syntax error → skipped, no crash
    assert mutable_default_args([tmp_path]) == []
