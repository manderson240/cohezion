#!/usr/bin/env python3
"""Flag ``exec()`` / ``eval()`` of non-literal code that runs with the FULL builtins module.

Fifth sibling of ``dormancy_scan`` / ``phantom_attr_scan`` / ``narrow_guard_scan`` /
``falsifiability_scan``: **"does generated code run with import/open/eval reachable?"**

ORIGIN (security finding H5): CPython auto-injects the real ``builtins`` module into any globals
dict lacking a ``"__builtins__"`` key, so ``exec(llm_code, {})`` and ``exec(llm_code, ns)`` both
expose ``__import__``/``open``/``eval``. ``cohezion.compound.safe_exec.safe_exec_globals`` fixed
the instances found in 2026-06; new call sites kept re-opening the class because nothing checked
(2026-09-13: 13 unrestricted sites in ``src/``, 5 of them executing LLM output).

A call is ACCEPTED when its globals argument is:
  * a call to ``safe_exec_globals(...)``;
  * a dict literal whose ``"__builtins__"`` value is an unpacking-free dict literal, or a name
    bound to one in the same scope (``{"__builtins__": {"abs": abs}}``);
  * a name bound, in the same scope, to either of the above.
Code given as a string literal is not generated, so it is skipped.

Deliberate exceptions carry an inline pragma WITH a reason, on the call line or the line above:
    # unrestricted-exec-ok: <why full builtins are required here>
A bare pragma without a reason does not count — the reason is the review artifact.

NOT a sandbox check: ``safe_exec`` is itself an availability gate, not a security boundary (see
its module docstring). This scan only stops the auto-injection hole from silently re-appearing.
Scope tracking is intraprocedural and flow-insensitive to branches; a namespace built in a helper
function reads as unrestricted and needs ``safe_exec_globals()`` inline or a pragma.

Usage:
    python scripts/ci/unrestricted_exec_scan.py [ROOT ...]   # default: src/
    python scripts/ci/unrestricted_exec_scan.py --self-test
"""

from __future__ import annotations

import ast
import re
import sys
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path


PRAGMA_RE = re.compile(r"#\s*unrestricted-exec-ok:\s*\S")
SAFE_FACTORY = "safe_exec_globals"
TARGETS = frozenset({"exec", "eval"})

# Binding kinds tracked per scope.
_SAFE = "safe"  # safe_exec_globals(...) or a dict literal with a restricted __builtins__
_PLAIN_DICT = "dict"  # any other unpacking-free dict literal (usable AS a restricted __builtins__)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    func: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.func}() {self.reason}"


def _is_safe_factory_call(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call):
        return False
    fn = node.func
    name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
    return name == SAFE_FACTORY


def _is_plain_dict_literal(node: ast.AST | None) -> bool:
    """A dict literal with no ``**`` unpacking — ``{**vars(builtins)}`` would smuggle the module in."""
    return isinstance(node, ast.Dict) and None not in node.keys


def _is_restricted_dict_literal(node: ast.AST | None, scope: dict[str, str]) -> bool:
    if not isinstance(node, ast.Dict) or not _is_plain_dict_literal(node):
        return False
    for key, value in zip(node.keys, node.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "__builtins__":
            if _is_plain_dict_literal(value):
                return True
            return isinstance(value, ast.Name) and scope.get(value.id) == _PLAIN_DICT
    return False


def _globals_arg(call: ast.Call) -> ast.AST | None:
    if len(call.args) >= 2:
        return call.args[1]
    for kw in call.keywords:
        if kw.arg == "globals":
            return kw.value
    return None


class _ScopeVisitor(ast.NodeVisitor):
    """Walks one file, tracking per-scope bindings of restricted namespaces in source order."""

    def __init__(self, path: Path, lines: list[str]) -> None:
        self.path = path
        self.lines = lines
        self.findings: list[Finding] = []
        self._scopes: list[dict[str, str]] = [{}]

    def _enter_scope(self, node: ast.AST) -> None:
        self._scopes.append({})
        self.generic_visit(node)
        self._scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter_scope(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._enter_scope(node)

    def _classify(self, value: ast.AST | None) -> str:
        scope = self._scopes[-1]
        if _is_safe_factory_call(value) or _is_restricted_dict_literal(value, scope):
            return _SAFE
        if isinstance(value, ast.Name) and scope.get(value.id) == _SAFE:
            return _SAFE
        return _PLAIN_DICT if _is_plain_dict_literal(value) else ""

    def _bind(self, target: ast.AST, value: ast.AST | None) -> None:
        if isinstance(target, ast.Name):
            self._scopes[-1][target.id] = self._classify(value)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        for target in node.targets:
            self._bind(target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)
        self._bind(node.target, node.value)

    def _has_pragma(self, line: int) -> bool:
        """Pragma on the call line, or anywhere in the contiguous comment block directly above."""
        idx = line - 1  # 1-based -> 0-based
        if 0 <= idx < len(self.lines) and PRAGMA_RE.search(self.lines[idx]):
            return True
        idx -= 1
        while 0 <= idx < len(self.lines) and self.lines[idx].lstrip().startswith("#"):
            if PRAGMA_RE.search(self.lines[idx]):
                return True
            idx -= 1
        return False

    def visit_Call(self, node: ast.Call) -> None:
        self.generic_visit(node)
        if not (isinstance(node.func, ast.Name) and node.func.id in TARGETS) or not node.args:
            return
        if isinstance(node.args[0], ast.Constant):
            return
        verdict = self._judge(_globals_arg(node))
        if verdict and not self._has_pragma(node.lineno):
            self.findings.append(Finding(self.path, node.lineno, node.func.id, verdict))

    def _judge(self, g: ast.AST | None) -> str | None:
        if g is None:
            return "has no globals argument (inherits the caller's full builtins)"
        if self._classify(g) == _SAFE:
            return None
        if isinstance(g, ast.Name):
            return f"globals {g.id!r} is not bound to a restricted namespace in this scope"
        return f"globals argument lacks a restricted '__builtins__' ({SAFE_FACTORY}() expected)"


def scan_file(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    try:
        with warnings.catch_warnings():  # docstring escape-sequence noise is not our signal
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    visitor = _ScopeVisitor(path, source.splitlines())
    visitor.visit(tree)
    return visitor.findings


def scan(roots: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in files:
            findings.extend(scan_file(path))
    return findings


# (label, source, expected finding count). Planted defects must be RED, fixes GREEN.
_SELF_TEST_CASES: list[tuple[str, str, int]] = [
    ("empty-dict globals (historical H5)", "def f(code):\n    exec(code, {})\n", 1),
    ("no globals at all", "def f(code):\n    exec(code)\n", 1),
    ("plain namespace dict", "def f(code):\n    ns = {}\n    exec(code, ns)\n", 1),
    ("eval with no globals", "def f(expr):\n    return eval(expr)\n", 1),
    (
        "builtins bound to real module",
        "import builtins\ndef f(c):\n    exec(c, {'__builtins__': builtins})\n",
        1,
    ),
    ("builtins via dunder name", "def f(c):\n    exec(c, {'__builtins__': __builtins__})\n", 1),
    (
        "builtins via unpacked dict",
        "import builtins\ndef f(c):\n    b = {**vars(builtins)}\n    exec(c, {'__builtins__': b})\n",
        1,
    ),
    (
        "unpacked outer dict",
        "def f(c, g):\n    exec(c, {'__builtins__': {}, **g})\n",
        1,
    ),
    (
        "rebound after safe",
        "def f(c):\n    ns = safe_exec_globals()\n    ns = {}\n    exec(c, ns)\n",
        1,
    ),
    ("safe name from OTHER scope", "ns = safe_exec_globals()\ndef f(c):\n    exec(c, ns)\n", 1),
    ("bare pragma, no reason", "def f(c):\n    exec(c, {})  # unrestricted-exec-ok:\n", 1),
    ("inline factory call", "def f(c):\n    exec(c, safe_exec_globals(np=1))\n", 0),
    ("bound from factory", "def f(c):\n    ns = safe_exec_globals()\n    exec(c, ns)\n", 0),
    ("module-attr factory", "def f(c):\n    exec(c, se.safe_exec_globals())\n", 0),
    ("restricted literal", "def f(c):\n    exec(c, {'__builtins__': {}}, {})\n", 0),
    (
        "named restricted literal",
        "def f(c, s):\n    g = {'__builtins__': {}}\n    return eval(c, g, s)\n",
        0,
    ),
    (
        "builtins via named dict",
        "def f(c):\n    b = {'abs': abs}\n    g = {'__builtins__': b}\n    exec(c, g)\n",
        0,
    ),
    ("string literal code", "exec('x = 1')\n", 0),
    (
        "pragma with reason",
        "def f(c):\n    # unrestricted-exec-ok: mutated repo source\n    exec(c, {})\n",
        0,
    ),
    (
        "pragma in comment block above",
        "def f(c):\n    # unrestricted-exec-ok: reason\n    # continues here\n    exec(c, {})\n",
        0,
    ),
    (
        "pragma separated by code",
        "def f(c):\n    # unrestricted-exec-ok: stale reason\n    x = 1\n    exec(c, {})\n",
        1,
    ),
    ("method named exec", "def f(db, c):\n    db.exec(c)\n", 0),
]


def self_test() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for idx, (label, source, expected) in enumerate(_SELF_TEST_CASES):
            path = Path(tmp) / f"case_{idx}.py"
            path.write_text(source, encoding="utf-8")
            got = len(scan_file(path))
            status = "ok" if got == expected else "FAIL"
            failures += got != expected
            print(f"[{status}] {label}: expected {expected}, got {got}")
    print(f"self-test: {len(_SELF_TEST_CASES) - failures}/{len(_SELF_TEST_CASES)} passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    roots = [Path(a) for a in argv if not a.startswith("-")] or [Path("src")]
    findings = scan(roots)
    for finding in findings:
        print(finding)
    print(f"unrestricted_exec_scan: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
