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
from dataclasses import dataclass
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


# Block statements that increase visual nesting depth (the "arrow anti-pattern").
_NEST_NODES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
)


def _max_nesting(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Deepest stack of block statements within a function's OWN body (item 47).

    Each ``if``/``for``/``while``/``with``/``try`` deepens its body by one level. Recursion stops at
    nested function/lambda boundaries, so a nested def's deep body does NOT inflate the enclosing
    function — each scope is scored on its own. A function with no blocks has depth 0.
    """
    max_depth = 0

    def _walk(node: ast.AST, depth: int) -> None:
        nonlocal max_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue  # a nested scope starts its own depth count
            if isinstance(child, _NEST_NODES):
                d = depth + 1
                max_depth = max(max_depth, d)
                _walk(child, d)  # its body/orelse/handlers are one level deeper
            else:
                _walk(child, depth)

    _walk(func, 0)
    return max_depth


def nesting_outliers(paths: Iterable[Path], *, threshold: int = 5) -> list[tuple[str, int]]:
    """Functions whose max block-nesting depth exceeds ``threshold``. READ-ONLY.

    The "arrow anti-pattern" (DEPTH) — how DEEP control blocks stack — the complement to item-43's
    cyclomatic complexity (BREADTH: how MANY branches). Returns ``[(<filename>::<funcname>, depth)]``
    for ``depth > threshold``, sorted by depth descending then name. A nested def is scored as its
    own function (its depth does not inflate the enclosing scope). Pure — reads source, no writes.
    """
    out: list[tuple[str, int]] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                depth = _max_nesting(node)
                if depth > threshold:
                    out.append((f"{path.name}::{node.name}", depth))
    return sorted(out, key=lambda t: (-t[1], t[0]))


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


def _param_count(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Parameter count of ``func`` — the data-clump dimension (item 63).

    Counts positional-only + positional + keyword-only params, plus ``*args`` and ``**kwargs`` as
    ONE each. A leading ``self``/``cls`` is excluded (by name — a method's receiver is not an
    argument the caller passes). Pure: inspects the AST node, never executes.
    """
    a = func.args
    positional = list(a.posonlyargs) + list(a.args)
    if positional and positional[0].arg in ("self", "cls"):
        positional = positional[1:]  # receiver is not a caller-supplied argument
    n = len(positional) + len(a.kwonlyargs)
    if a.vararg is not None:
        n += 1  # *args counts as one
    if a.kwarg is not None:
        n += 1  # **kwargs counts as one
    return n


def long_parameter_lists(paths: Iterable[Path], *, threshold: int = 6) -> list[tuple[str, int]]:
    """Functions whose parameter count exceeds ``threshold`` — the data-clump smell (item 63). READ-ONLY.

    Returns ``[(qualified_name, param_count)]`` for every function/method with ``params > threshold``,
    sorted by ``param_count`` descending then name. ``self``/``cls`` excluded; ``*args``/``**kwargs``
    each count as one (see :func:`_param_count`). A clean/empty set of files → ``[]``. Pure (stdlib
    ast, no writes) — a number is a smell flagged for judgment, not a verdict.
    """
    out: list[tuple[str, int]] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue  # unreadable / not valid Python → skip, never crash the audit
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                count = _param_count(node)
                if count > threshold:
                    out.append((f"{path.name}::{node.name}", count))
    return sorted(out, key=lambda t: (-t[1], t[0]))


def _func_span(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Source-line span of ``func`` — the SIZE dimension (item 64).

    ``end_lineno - lineno + 1`` (inclusive of both the ``def`` line and the last body line). The span
    of a function CONTAINING a nested def includes the nested lines; the nested def is reported
    separately by :func:`long_functions` (``ast.walk`` visits it too). Pure: inspects the AST node.
    """
    end = func.end_lineno if func.end_lineno is not None else func.lineno
    return end - func.lineno + 1


def long_functions(paths: Iterable[Path], *, threshold: int = 50) -> list[tuple[str, int]]:
    """Functions whose source span exceeds ``threshold`` — the SIZE smell (item 64). READ-ONLY.

    Returns ``[(qualified_name, span)]`` for every function/method with ``span > threshold``, sorted
    by ``span`` descending then name. Distinct from cyclomatic complexity (item 43): a long function
    can be flat yet still hard to hold in the head. Nested defs appear as their own entries. A
    clean/empty set of files → ``[]``. Pure (stdlib ast ``end_lineno``, no writes) — a line count is
    a smell flagged for judgment, not a verdict.
    """
    out: list[tuple[str, int]] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue  # unreadable / not valid Python → skip, never crash the audit
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                span = _func_span(node)
                if span > threshold:
                    out.append((f"{path.name}::{node.name}", span))
    return sorted(out, key=lambda t: (-t[1], t[0]))


_CATCHALL_EXCEPTIONS = frozenset({"Exception", "BaseException"})


def _exception_names(node: ast.expr) -> set[str]:
    """The exception type names in an ``except`` clause (a Name, an Attribute's attr, or a Tuple)."""
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}  # e.g. builtins.Exception → "Exception"
    if isinstance(node, ast.Tuple):
        names: set[str] = set()
        for elt in node.elts:
            names |= _exception_names(elt)
        return names
    return set()


def stealth_bare_excepts(paths: Iterable[Path]) -> list[tuple[str, str]]:
    """Flag bare-except handlers, including STEALTH ones hiding in a tuple (item 65, L359). READ-ONLY.

    Returns ``[(location, kind)]`` for each `except` that catches everything: ``kind`` is ``"bare"``
    (a truly bare ``except:``), ``"Exception"``/``"BaseException"`` (a single catch-all), or
    ``"stealth-tuple"`` (a tuple CONTAINING ``Exception``/``BaseException`` — L359: because the
    supertype is present, ``except (ValueError, Exception):`` is semantically ``except Exception:``).
    A sibling-only tuple (``except (ImportError, KeyError):``) is NOT flagged. ``location`` is
    ``<relpath>:<lineno>``. Report-only — a candidate to narrow, a human call. Pure (stdlib ast).
    """
    out: list[tuple[str, str]] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue  # unreadable / not valid Python → skip, never crash the audit
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            loc = f"{path.name}:{node.lineno}"
            if node.type is None:
                out.append((loc, "bare"))
                continue
            names = _exception_names(node.type)
            catchall = names & _CATCHALL_EXCEPTIONS
            if not catchall:
                continue  # narrow / sibling-only → legitimate
            if isinstance(node.type, ast.Tuple):
                out.append((loc, "stealth-tuple"))
            else:
                out.append((loc, sorted(catchall)[0]))
    return sorted(out)


# Decorators that make single-call forwarding LEGITIMATE (required indirection, not a smell).
_INDIRECTION_DECORATORS = frozenset(
    {"property", "cached_property", "abstractmethod", "abstractproperty"}
)


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _forwards_only_names(call: ast.Call) -> bool:
    """True iff the call's arguments are pure forwarding — bare names or *name/**name — with NO
    literals, operators, or nested calls (any of which would be *added logic*, not a pass-through)."""

    def _ok_arg(a: ast.expr) -> bool:
        if isinstance(a, ast.Name):
            return True
        return isinstance(a, ast.Starred) and isinstance(a.value, ast.Name)

    return all(_ok_arg(a) for a in call.args) and all(
        isinstance(k.value, ast.Name) for k in call.keywords
    )


def _is_passthrough(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    name = func.name
    if name.startswith("__") and name.endswith("__"):
        return False  # dunders (e.g. __init__ → super().__init__()) are legit forwarding
    for dec in func.decorator_list:
        dname = (
            dec.id
            if isinstance(dec, ast.Name)
            else dec.attr
            if isinstance(dec, ast.Attribute)
            else None
        )
        if dname in _INDIRECTION_DECORATORS:
            return False  # property / abstractmethod: required indirection
    body = _strip_docstring(func.body)
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
        call: ast.Call = stmt.value
    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
    else:
        return False
    return _forwards_only_names(call)


def passthrough_functions(paths: Iterable[Path]) -> list[str]:
    """Functions whose entire body forwards to ONE call with no added logic. READ-ONLY.

    The wrapper-that-earns-nothing (item 44) — the dual of an orphan: present but meaningless. A
    body that is a single ``return g(...)`` / ``g(...)`` forwarding only bare names is flagged;
    any added logic (a literal/operator/nested-call argument, a branch, >1 statement, a non-call
    return), a dunder, or a ``@property``/``@abstractmethod`` is NOT (legit indirection). Returns
    sorted ``<relpath>::<funcname>``. Report-only — a candidate for inlining (a human call), never
    auto-inlined. Pure: reads source, never writes.
    """
    out: list[str] = []
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _is_passthrough(node):
                out.append(f"{path.name}::{node.name}")
    return sorted(out)


@dataclass(frozen=True)
class NeedlessPassthrough:
    """A forwarder narrowed by reachability (item 46). ``orphan`` = zero static callers."""

    qualified_name: str
    caller_count: int
    orphan: bool


def _call_name(node: ast.Call) -> str | None:
    """The called name of a Call: bare ``f()`` → 'f', attribute ``x.f()`` → 'f'."""
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return None


def _caller_counts(paths: Iterable[Path]) -> dict[str, int]:
    """Count call expressions per called name across the paths (both ``f()`` and ``x.f()``)."""
    counts: dict[str, int] = {}
    for path in _iter_python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name:
                    counts[name] = counts.get(name, 0) + 1
    return counts


def needless_passthroughs(paths: Iterable[Path]) -> list[NeedlessPassthrough]:
    """Item-44 forwarders with <=1 static caller — the wrapper that earns nothing. READ-ONLY.

    Narrows ``passthrough_functions`` by reachability: a forwarder called from exactly ONE site is
    needless indirection; one called from ZERO sites is also an orphan (kept, ``orphan=True``); one
    called from >=2 sites is a FACADE (a real API surface) and is dropped. Counting is by called
    NAME across the paths (conservative: a same-named function elsewhere inflates the count toward
    "facade", so the report errs AWAY from false "needless" flags). Pure — reads source, no writes.
    """
    plist = list(paths)
    forwarders = passthrough_functions(plist)
    counts = _caller_counts(plist)
    out: list[NeedlessPassthrough] = []
    for q in forwarders:
        name = q.split("::")[-1]
        count = counts.get(name, 0)
        if count <= 1:
            out.append(NeedlessPassthrough(qualified_name=q, caller_count=count, orphan=count == 0))
    return sorted(out, key=lambda n: n.qualified_name)
