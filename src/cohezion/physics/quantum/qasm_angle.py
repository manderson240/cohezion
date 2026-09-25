"""Evaluate a QASM gate-angle expression without ``eval()``.

QASM files are third-party input. ``eval()`` with empty ``__builtins__`` is not a
sandbox (attribute walks such as ``().__class__.__base__`` reach everything), and a
character-class pre-filter still admits ``**``, so the old path would compute
``9**9**9**9`` on request. This walks the AST against a closed grammar instead:
numbers, ``pi``, ``+ - * /``, unary ``+``/``-`` and parentheses. Anything else raises
``ValueError``; nothing is executed.

Kept dependency-free so it is importable (and testable) without quimb/cotengra.
"""

from __future__ import annotations

import ast
import math
import operator


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def parse_qasm_angle(expr: str) -> float:
    """Return the value of a QASM angle expression such as ``"-pi/2"`` or ``"1.3+pi"``.

    Raises:
        ValueError: the expression is outside the grammar, is malformed, divides by
            zero, or is not finite.
    """

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id == "pi":
            return math.pi
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            return _BINARY[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported QASM angle expression: {expr!r}")

    try:
        value = float(_eval(ast.parse(expr.strip(), mode="eval")))
    except (SyntaxError, ZeroDivisionError, RecursionError, MemoryError, OverflowError) as e:
        # MemoryError: parser stack overflow on deep nesting; OverflowError: int literal
        # too large for float.
        raise ValueError(f"Failed to parse QASM angle expression: {expr!r}") from e
    if not math.isfinite(value):
        raise ValueError(f"Non-finite QASM angle: {expr!r}")
    return value
