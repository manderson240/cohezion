#!/usr/bin/env python3
"""Lint rule: flag `except (A, B):` where one exception is a subclass of another.

Rationale: `except (ImportError, Exception):` looks narrow but is semantically
`except Exception:` because `ImportError` is an `Exception` subclass. The
tuple member `ImportError` is redundant. Bugs hidden behind this pattern:
silent swallowing of `MemoryError`, `KeyboardInterrupt` subclasses, and
custom domain errors the caller wanted to handle.

See:
- src/cohezion/knowledge_graph/KEY_LEARNINGS.md L359
- ~/vaults/cohezion-vault/cerebellum/patterns/2026-04-18-except-tuple-subclass-bareness.md
- CLAUDE.md Coding Standards -> Error handling

Usage:
    uv run python scripts/lint/check_except_subclass.py src/
    uv run python scripts/lint/check_except_subclass.py path/to/specific.py

Exit:
    0 — no violations
    1 — violations found (printed to stderr)
    2 — usage / IO error

Detects only direct standard-library subclass relationships (builtins module).
Does NOT resolve custom exception class hierarchies — those are out of scope.
Examples that would be flagged:
    except (ImportError, Exception):        # ImportError is an Exception
    except (FileNotFoundError, OSError):    # FileNotFoundError inherits from OSError
    except (TimeoutError, Exception):       # TimeoutError is an Exception
"""

from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path


def _resolve_builtin_exception(name: str) -> type | None:
    """Return the built-in exception class for a bare name, or None."""
    obj = getattr(builtins, name, None)
    if isinstance(obj, type) and issubclass(obj, BaseException):
        return obj
    return None


def _resolve_attr_exception(attr_chain: list[str]) -> type | None:
    """Resolve dotted names like asyncio.TimeoutError -> the class (best effort)."""
    if len(attr_chain) != 2:
        return None
    module_name, cls_name = attr_chain
    try:
        module = __import__(module_name, fromlist=[cls_name])
    except (ImportError, AttributeError, ValueError):
        return None
    obj = getattr(module, cls_name, None)
    if isinstance(obj, type) and issubclass(obj, BaseException):
        return obj
    return None


def _name_from_node(node: ast.AST) -> str | None:
    """Return a human-readable name for an exception type expr in an except handler."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    return None


def _resolve(node: ast.AST) -> type | None:
    if isinstance(node, ast.Name):
        return _resolve_builtin_exception(node.id)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return _resolve_attr_exception([node.value.id, node.attr])
    return None


def check_file(path: Path) -> list[tuple[int, str]]:
    """Return (line, message) tuples for each violation."""
    try:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, OSError) as exc:
        print(f"{path}: parse error: {exc}", file=sys.stderr)
        return []

    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None or not isinstance(node.type, ast.Tuple):
            continue

        resolved_types: list[tuple[str, type]] = []
        for elt in node.type.elts:
            cls = _resolve(elt)
            if cls is not None:
                resolved_types.append((_name_from_node(elt) or str(cls), cls))

        # Compare each pair
        for i, (name_a, cls_a) in enumerate(resolved_types):
            for name_b, cls_b in resolved_types[i + 1 :]:
                if cls_a is cls_b:
                    continue
                if issubclass(cls_a, cls_b):
                    violations.append(
                        (
                            node.lineno,
                            f"{name_a} is a subclass of {name_b}; "
                            f"`except ({name_a}, {name_b})` is equivalent to "
                            f"`except {name_b}` — remove {name_a}",
                        )
                    )
                elif issubclass(cls_b, cls_a):
                    violations.append(
                        (
                            node.lineno,
                            f"{name_b} is a subclass of {name_a}; "
                            f"`except (..., {name_b}, ..., {name_a})` is equivalent to "
                            f"`except {name_a}` — remove {name_b}",
                        )
                    )
    return violations


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    targets = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"path not found: {p}", file=sys.stderr)
            return 2
        if p.is_file():
            if p.suffix == ".py":
                targets.append(p)
        else:
            targets.extend(p.rglob("*.py"))

    total = 0
    for path in targets:
        for line, msg in check_file(path):
            print(f"{path}:{line}: {msg}", file=sys.stderr)
            total += 1

    if total:
        print(f"\n{total} violation(s) across {len(targets)} files", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
