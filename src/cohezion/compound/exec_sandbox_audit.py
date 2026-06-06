"""Executor↔sandbox coverage audit (item 48, 2026-06-06) — report-only.

Prompted by langchain.com "give your AI agent its own computer" — its PRINCIPLE ("agents run
untrusted code by definition"), NOT its cloud-microVM product (which conflicts with local-$0/CC2).
Cohezion already has ``sandbox/isolation.py`` (``IsolationContext``) + ``sandbox/shadow_worktree.py``.
The open question: does any code path run dynamically-executed code WITHOUT entering isolation?

This instrument scans for dynamic-code-execution sinks (``exec``/``eval``/``subprocess.*``/
``os.system``/``os.popen``) and flags those NOT lexically inside an ``IsolationContext`` (or any
``with`` whose context manager name contains "isolation"/"sandbox"). Report-only: a real finding is
a separate permission-gated remediation, and a sink that runs only static/first-party code is a
false positive for a human to triage (a list is a smell, not a verdict). Pure — reads source, no writes.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


_BARE_SINKS = {"exec", "eval"}
_SUBPROCESS_SINKS = {"run", "Popen", "call", "check_call", "check_output"}
_OS_SINKS = {"system", "popen"}


@dataclass(frozen=True)
class ExecSite:
    """A dynamic-code-execution sink. ``location`` is ``<filename>:<line>``."""

    location: str
    sink: str
    sandboxed: bool  # lexically inside an IsolationContext/sandbox `with` block


def _iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for p in paths:
        if p.is_dir():
            yield from sorted(p.rglob("*.py"))
        elif p.suffix == ".py":
            yield p


def _sink_name(call: ast.Call) -> str | None:
    """The execution-sink name of a Call, or None if it is not a code-exec sink."""
    fn = call.func
    if isinstance(fn, ast.Name) and fn.id in _BARE_SINKS:
        return fn.id
    if isinstance(fn, ast.Attribute):
        root = fn.value
        rootname = root.id if isinstance(root, ast.Name) else ""
        if rootname == "subprocess" and fn.attr in _SUBPROCESS_SINKS:
            return f"subprocess.{fn.attr}"
        if rootname == "os" and fn.attr in _OS_SINKS:
            return f"os.{fn.attr}"
    return None


def _with_is_isolation(node: ast.With | ast.AsyncWith) -> bool:
    """True iff any context manager of this ``with`` names isolation/sandbox."""
    for item in node.items:
        ctx = item.context_expr
        func = ctx.func if isinstance(ctx, ast.Call) else ctx
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        else:
            name = ""
        low = name.lower()
        if "isolation" in low or "sandbox" in low:
            return True
    return False


def _scan(node: ast.AST, inside_iso: bool, out: list[ExecSite], path: Path) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.With | ast.AsyncWith):
            iso = inside_iso or _with_is_isolation(child)
            for item in child.items:  # the context expr itself is evaluated at the OUTER level
                _scan(item.context_expr, inside_iso, out, path)
            for stmt in child.body:
                _scan(stmt, iso, out, path)
            continue
        if isinstance(child, ast.Call):
            sink = _sink_name(child)
            if sink is not None:
                out.append(ExecSite(f"{path.name}:{child.lineno}", sink, inside_iso))
        _scan(child, inside_iso, out, path)


def unsandboxed_exec_paths(paths: Iterable[Path]) -> list[ExecSite]:
    """Dynamic-code-exec sinks NOT inside an IsolationContext/sandbox `with`. READ-ONLY.

    Returns only the UNSANDBOXED sites (``sandboxed`` is False), sorted by location. A sink inside
    an isolation `with` block is clean (omitted); a plain `with open(...)` is NOT isolation, so an
    exec inside it is still flagged. Pure — reads source, never writes.
    """
    out: list[ExecSite] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        sites: list[ExecSite] = []
        _scan(tree, False, sites, path)
        out.extend(s for s in sites if not s.sandboxed)
    return sorted(out, key=lambda s: s.location)
