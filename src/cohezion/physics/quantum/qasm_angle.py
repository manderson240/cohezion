"""Evaluate a QASM gate-angle expression without ``eval()``.

QASM files are third-party input. The previous parser ran ``eval()`` with empty
``__builtins__`` after a character-class filter. Empty builtins is not a sandbox, and
the filter admitted ``**``, so ``9**9**9**9`` was a CPU/memory bomb on request. This
module never executes the input: a length cap and a lexical filter bound the input,
then the AST is walked against a closed grammar -- decimal numbers, ``pi``,
``+ - * /``, unary ``+``/``-`` and parentheses. Anything else raises ``ValueError``.

Kept dependency-free so it is importable (and testable) without quimb/cotengra.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from collections.abc import Callable


# Real tracker angles are <= 23 characters; the cap bounds ast.parse cost
# (a 10 MB expression costs seconds and gigabytes before any grammar check).
MAX_EXPR_LEN = 256
# Lexical grammar: decimal digits, '.', exponent 'e'/'E', operators, parentheses,
# whitespace and the token 'pi'. Rejects hex/binary literals, '_' separators,
# comments, quotes and every identifier other than pi.
_LEXICAL = re.compile(r"(?:[0-9.eE+\-*/()\s]|pi)*")

_BINARY: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def parse_qasm_angle(expr: str) -> float:
    """Return the value of a QASM angle expression such as ``"-pi/2"`` or ``"1.3+pi"``.

    Raises:
        ValueError: the input is not a string, is too long, is outside the grammar,
            is malformed, divides by zero, or is not finite.
    """
    if not isinstance(expr, str):
        raise ValueError(f"QASM angle must be a string, got {type(expr).__name__}")
    shown = expr if len(expr) <= 64 else expr[:64] + "..."
    if len(expr) > MAX_EXPR_LEN:
        raise ValueError(f"QASM angle expression longer than {MAX_EXPR_LEN} chars: {shown!r}")
    if not _LEXICAL.fullmatch(expr):
        raise ValueError(f"Unsupported characters in QASM angle expression: {shown!r}")

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
        raise ValueError(f"Unsupported QASM angle expression: {shown!r}")

    try:
        value = float(_eval(ast.parse(expr.strip(), mode="eval")))
    except (SyntaxError, ZeroDivisionError, RecursionError, MemoryError, OverflowError) as e:
        # Defensive: the length cap already rules out parser-stack and recursion blowups.
        raise ValueError(f"Failed to parse QASM angle expression: {shown!r}") from e
    if not math.isfinite(value):
        raise ValueError(f"Non-finite QASM angle: {shown!r}")
    return value
