"""Elegant-simplicity audit — READ-ONLY instruments that flag complexity smells (items 43/44).

The audit loop's "elegant simplicity" dimension (user request 2026-06-06). These measure the
structural COST of code and flag OUTLIERS for human/build-loop judgment. Guardrails (see
docs/IMPROVEMENT_BACKLOG.md Notes): OBJECTIVE metrics only (a number is a smell, not a verdict);
REPORT-ONLY (never auto-refactor); complexity, like an import edge, must EARN ITS KEEP.

- ``complexity_outliers`` (item 43): McCabe cyclomatic complexity per function — control-flow
  complexity (the vertical complement to item-10's LCOM4 cohesion = horizontal).
- ``passthrough_functions`` (item 44): the wrapper-that-earns-nothing — a function whose whole
  body forwards to one call with no added logic (the dual of an orphan: present-but-meaningless).
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path


# Cyclomatic-complexity decision-point node types. Each occurrence adds 1 to the base of 1.
# (BoolOp is handled separately — it adds len(values)-1, one per `and`/`or` operator.)
_DECISION_NODES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.Assert,
    ast.IfExp,  # ternary  a if c else b
    ast.match_case,
)


def _cyclomatic_complexity(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """McCabe cyclomatic complexity of one function: 1 + decision points within its OWN body.

    Counts If/For/While/except/assert/ternary/match-case (+1 each), each `if` clause of a
    comprehension (+1), and each boolean operator (`and`/`or` → +len(values)-1). Recursion stops
    at nested function/lambda boundaries, so a nested def's branches do NOT inflate the enclosing
    function — each scope is scored on its own (exact, not approximate).
    """
    complexity = 1

    def _count(node: ast.AST) -> None:
        nonlocal complexity
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue  # a nested scope is scored separately — do not descend
            if isinstance(child, _DECISION_NODES):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += len(child.ifs)
            _count(child)

    _count(func)
    return complexity


def _iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for p in paths:
        if p.is_dir():
            yield from sorted(p.rglob("*.py"))
        elif p.suffix == ".py":
            yield p


def complexity_outliers(paths: Iterable[Path], *, threshold: int = 15) -> list[tuple[str, int]]:
    """Functions whose cyclomatic complexity exceeds ``threshold``. READ-ONLY.

    Returns ``[(qualified_name, cc)]`` for every function/method with ``cc > threshold``, sorted
    by ``cc`` descending then name. ``qualified_name`` is ``<relpath>::<funcname>``. A clean/empty
    set of files → ``[]``. Pure: reads source, never writes; no third-party dependency.
    """
    out: list[tuple[str, int]] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue  # unreadable / not valid Python → skip, never crash the audit
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                cc = _cyclomatic_complexity(node)
                if cc > threshold:
                    out.append((f"{path.name}::{node.name}", cc))
    return sorted(out, key=lambda t: (-t[1], t[0]))
