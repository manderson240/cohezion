#!/usr/bin/env python3
"""Comment/docstring-aware filter for check_inference_port_bypass.sh.

grep is line-based and can't tell a hardcoded dispatch port from a port number
mentioned in a `#` comment or a docstring banner table. This does that
distinction using the ast (docstring spans: bare string-literal expression
statements — module/class/function docstrings and inline banner strings) and
tokenize (comment spans) modules, which grep has no access to.

Reads "file:line:content" triples on stdin (already past the bash script's
inline-override and path-based allow-listing) and re-emits only the lines
whose port-number match is NOT inside a comment or docstring span — i.e. the
real violations. Fails open per-file: if a file won't parse/tokenize, every
candidate line in it is treated as a real violation (never silently hidden by
a parse error).
"""

from __future__ import annotations

import ast
import re
import sys
import tokenize


PATTERN = re.compile(r"\b1330[6-9]\b")


def _docstring_lines(source: str) -> set[int]:
    """Line numbers covered by a bare string-literal expression statement."""
    lines: set[int] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            start = node.value.lineno
            end = getattr(node.value, "end_lineno", start)
            lines.update(range(start, end + 1))
    return lines


def _comment_start_cols(source: str) -> dict[int, int]:
    """Line number -> column where a `#` comment begins on that line."""
    cols: dict[int, int] = {}
    tokens = tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__)
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            cols[tok.start[0]] = tok.start[1]
    return cols


def is_real_violation(
    lineno: int, content: str, doc_lines: set[int], comment_cols: dict[int, int]
) -> bool:
    if lineno in doc_lines:
        return False
    code_part = content[: comment_cols[lineno]] if lineno in comment_cols else content
    return bool(PATTERN.search(code_part))


def main() -> int:
    by_file: dict[str, list[tuple[int, str]]] = {}
    order: list[str] = []
    for raw in sys.stdin:
        raw = raw.rstrip("\n")
        if not raw:
            continue
        file, lineno_s, content = raw.split(":", 2)
        by_file.setdefault(file, []).append((int(lineno_s), content))
        order.append(raw)

    kept_lines: set[str] = set()
    for file, entries in by_file.items():
        try:
            with open(file, encoding="utf-8") as f:
                source = f.read()
            doc_lines = _docstring_lines(source)
            comment_cols = _comment_start_cols(source)
        except (OSError, SyntaxError, tokenize.TokenError, UnicodeDecodeError):
            # Fail open: can't classify this file, so don't hide anything in it.
            for lineno, content in entries:
                kept_lines.add(f"{file}:{lineno}:{content}")
            continue
        for lineno, content in entries:
            if is_real_violation(lineno, content, doc_lines, comment_cols):
                kept_lines.add(f"{file}:{lineno}:{content}")

    for raw in order:
        if raw in kept_lines:
            print(raw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
