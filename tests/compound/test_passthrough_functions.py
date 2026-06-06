"""Discriminating tests for the needless-indirection / pass-through report (item 44, 2026-06-06).

`passthrough_functions(paths)` flags a function whose entire body forwards to ONE call with no
added logic — the wrapper-that-earns-nothing. Each test fails a plausible wrong impl:
  - flag anything returning a value (ignore "is it a bare forward?") → T_added_logic,
  - flag multi-statement bodies → T_two_stmt,
  - flag arg-reshaping forwards → T_literal_arg,
  - flag dunders / @property (legit indirection) → T_dunder / T_property,
  - miss the canonical *args/**kwargs forwarder → T_star,
  - crash on a broken file → T_badfile.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.simplicity_audit import passthrough_functions


def _scan(tmp_path: Path, src: str) -> list[str]:
    (tmp_path / "m.py").write_text(src)
    return passthrough_functions([tmp_path])


def test_bare_forward_is_flagged(tmp_path: Path) -> None:
    assert _scan(tmp_path, "def f(x):\n    return g(x)\n") == ["m.py::f"]


def test_star_kwargs_forward_is_flagged(tmp_path: Path) -> None:
    # The canonical pass-through wrapper.
    assert _scan(tmp_path, "def f(*a, **k):\n    return g(*a, **k)\n") == ["m.py::f"]


def test_added_logic_is_not_flagged(tmp_path: Path) -> None:
    # return value is an expression (g(x)+1), not a bare call → carries logic → NOT a pass-through.
    assert _scan(tmp_path, "def f(x):\n    return g(x) + 1\n") == []


def test_arg_reshaping_is_not_flagged(tmp_path: Path) -> None:
    # A literal argument reshapes the call → adds value → NOT a pure forward.
    assert _scan(tmp_path, "def f(x):\n    return g(x, 5)\n") == []


def test_multi_statement_body_is_not_flagged(tmp_path: Path) -> None:
    assert _scan(tmp_path, "def f(x):\n    y = g(x)\n    return y\n") == []


def test_nested_call_argument_is_not_flagged(tmp_path: Path) -> None:
    # g(h(x)) is composition (adds value), not a bare forward.
    assert _scan(tmp_path, "def f(x):\n    return g(h(x))\n") == []


def test_dunder_and_property_are_excluded(tmp_path: Path) -> None:
    src = (
        "class C:\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"  # dunder — legit forward
        "    @property\n"
        "    def x(self):\n"
        "        return self._compute()\n"  # property — required indirection
    )
    assert _scan(tmp_path, src) == []


def test_docstring_only_forward_still_flagged(tmp_path: Path) -> None:
    # A docstring + single forwarding return is still a pass-through (docstring is stripped).
    assert _scan(tmp_path, 'def f(x):\n    """doc."""\n    return g(x)\n') == ["m.py::f"]


def test_broken_file_skipped(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("def f(x):\n    return g(x)\n")
    (tmp_path / "bad.py").write_text("def (((:\n")
    assert passthrough_functions([tmp_path]) == ["ok.py::f"]
