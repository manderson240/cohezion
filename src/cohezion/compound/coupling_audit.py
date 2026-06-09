"""Control-coupling audit — boolean-flag-argument detector (item 97), report-only.

A "flag argument" — a parameter whose default is a boolean literal — is the classic CONTROL
COUPLING smell: the caller passes ``True``/``False`` to switch the function between behaviors, so
the function secretly does N things instead of being split into N functions (Fowler, clean-code
canon). This is DISTINCT from raw parameter count (item 63) and function size (item 64): a
two-parameter function can be a worse coupling smell than a six-parameter one if two of them are
flags. Mirrors the AST walk of ``simplicity_audit`` (items 43/65/110) but lives in its own module
because ``simplicity_audit`` is at the 500-line hard limit. Pure — stdlib ast, no writes.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path


def _iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for p in paths:
        if p.is_dir():
            yield from sorted(p.rglob("*.py"))
        elif p.suffix == ".py":
            yield p


def _boolean_default_count(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Number of the function's parameters whose DEFAULT is a boolean literal (``True``/``False``).

    Counts positional-or-keyword defaults (``args.defaults``) and keyword-only defaults
    (``args.kw_defaults``, skipping the ``None`` placeholders for kwonly args without a default).
    A boolean literal is an ``ast.Constant`` whose value satisfies ``isinstance(v, bool)`` — which
    is why ``0`` / ``1`` / ``""`` / ``None`` are NOT counted (``isinstance(0, bool)`` is ``False``),
    even though ``0 == False``. ``self``/``cls`` have no default, so they never count.
    """
    defaults = list(func.args.defaults) + [d for d in func.args.kw_defaults if d is not None]
    return sum(1 for d in defaults if isinstance(d, ast.Constant) and isinstance(d.value, bool))


def boolean_flag_params(paths: Iterable[Path], *, threshold: int = 2) -> list[tuple[str, int]]:
    """Functions with ``>= threshold`` boolean-default (flag) parameters (item 97). READ-ONLY.

    The "this function secretly does N things" smell: it branches on caller intent (a ``True``/
    ``False`` flag) rather than being split. Returns ``[(<filename>::<funcname>, flag_count)]`` for
    every function whose boolean-default count is ``>= threshold``, sorted by count descending then
    name. A single flag is NOT a smell (default ``threshold=2``); a non-boolean default
    (``0``/``""``/``None``) is NOT a flag; a positional param with no default is NOT counted.
    Pure — no writes; a missing/unparseable file is skipped, never raised.
    """
    out: list[tuple[str, int]] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                count = _boolean_default_count(node)
                if count >= threshold:
                    out.append((f"{path.name}::{node.name}", count))
    return sorted(out, key=lambda t: (-t[1], t[0]))
