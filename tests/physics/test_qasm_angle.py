"""QASM angle evaluator: closed grammar, no eval().

`2**10` is the discriminating probe: it passes the old character-class filter and the
old eval() path computed it (1024.0). `().__class__` is rejected by both old and new
code, so it guards the grammar but does not by itself prove eval() is gone.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from cohezion.physics.quantum.qasm_angle import parse_qasm_angle


_PEAKED = Path(__file__).parents[2] / "src/cohezion/physics/quantum/peaked_solver.py"


@pytest.mark.parametrize(
    ("expr", "expected"),
    [
        ("pi/2", math.pi / 2),
        ("-pi", -math.pi),
        ("3.14", 3.14),
        ("pi*0.5", math.pi * 0.5),
        ("-1.3+pi", -1.3 + math.pi),
        (" 1e-3 ", 1e-3),
        ("+2", 2.0),
        ("pi*(1/2)", math.pi / 2),
    ],
)
def test_valid_angles(expr: str, expected: float) -> None:
    assert parse_qasm_angle(expr) == pytest.approx(expected, abs=1e-15)


@pytest.mark.parametrize(
    "expr",
    [
        "().__class__",
        "().__class__.__base__.__subclasses__()",
        "__import__('os').system('true')",
        "pi.__class__",
        "2**10",  # passed the old regex; old eval() returned 1024.0
        "9//2",
        "True",
        "e",
        "abs(-1)",
        "[1][0]",
        "1 if 1 else 0",
        "",
        "1/0",
        "pi/",
        "1e999",  # inf
        "1e999-1e999",  # nan
        "1" + "0" * 400,  # int too large for float -> OverflowError
        "-" * 10000 + "1",  # parser stack overflow -> MemoryError
        "(" * 2000 + "1" + ")" * 2000,  # deep nesting
        "+".join(["1"] * 5000),  # deep BinOp chain -> RecursionError in the walker
    ],
    ids=lambda e: e[:24],
)
def test_rejects_everything_outside_the_grammar(expr: str) -> None:
    with pytest.raises(ValueError):
        parse_qasm_angle(expr)


def test_peaked_solver_no_longer_calls_eval() -> None:
    """Any call to eval/exec/compile, bare or as an attribute (builtins.eval)."""
    tree = ast.parse(_PEAKED.read_text())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    assert not called & {"eval", "exec", "compile"}
    assert "parse_qasm_angle" in called
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"eval", "exec", "__builtins__"}


def test_peaked_solver_parser_delegates_to_ast_evaluator() -> None:
    pytest.importorskip("cotengra")
    pytest.importorskip("quimb")
    from cohezion.physics.quantum.peaked_solver import _safe_parse_qasm_param

    assert _safe_parse_qasm_param("pi/2") == pytest.approx(math.pi / 2)
    with pytest.raises(ValueError):
        _safe_parse_qasm_param("2**10")
