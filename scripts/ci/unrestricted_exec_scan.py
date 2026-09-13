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
A tracked namespace is TAINTED by later mutation that could re-admit builtins
(``ns["__builtins__"] = ...``, ``ns.update(<opaque or dangerous>)``, ``ns |= ...``), and any
``DANGEROUS_NAMES`` reference (``builtins``, ``__import__``, ``open``, ``os``, ...) inside a
namespace expression voids it. Adding benign keys (``ns["np"] = np``) does not taint.

KNOWN LIMITS (measured by adversarial review, 2026-09-13; do not read green as exhaustive):
  * Misses: ``builtins.exec``/aliased ``exec``, ``types.FunctionType(code, {})``,
    ``code.InteractiveInterpreter``; branch-dependent bindings (last write wins, flow-insensitive);
    rebinding via for/with/tuple/walrus targets.
  * False positives: namespace built in a helper, held on ``self``, captured by a closure, bound
    by tuple/walrus, or ``{**safe_exec_globals(), ...}``. Use ``safe_exec_globals()`` inline or
    a pragma with a reason.
  * Default root is ``src/`` only. ``scripts/`` and ``experiments/`` contain LLM-code exec sites
    (12 findings in ``scripts/`` at introduction) that are NOT gated.

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


# Names whose presence inside a namespace hands generated code the capability the restriction
# exists to deny. Their appearance anywhere in a namespace expression voids "restricted".
DANGEROUS_NAMES = frozenset(
    {
        "__builtins__",
        "__import__",
        "builtins",
        "compile",
        "ctypes",
        "eval",
        "exec",
        "globals",
        "importlib",
        "open",
        "os",
        "shutil",
        "socket",
        "subprocess",
        "sys",
        "vars",
    }
)


def _mentions_dangerous_name(node: ast.AST | None) -> bool:
    return node is not None and any(
        isinstance(n, ast.Name) and n.id in DANGEROUS_NAMES for n in ast.walk(node)
    )


def _builtins_entry(node: ast.Dict) -> ast.AST | None:
    """Value of the LAST ``"__builtins__"`` key — duplicate keys resolve last-wins at runtime."""
    found = None
    for key, value in zip(node.keys, node.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "__builtins__":
            found = value
    return found


def _is_restricted_dict_literal(node: ast.AST | None, scope: dict[str, str]) -> bool:
    if not isinstance(node, ast.Dict) or not _is_plain_dict_literal(node):
        return False
    value = _builtins_entry(node)
    if value is None:
        return False
    if any(_mentions_dangerous_name(v) for v in node.values if v is not value):
        return False
    if _is_plain_dict_literal(value):
        return not _mentions_dangerous_name(value)
    return isinstance(value, ast.Name) and scope.get(value.id) == _PLAIN_DICT


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
        if isinstance(value, ast.Call) and _is_safe_factory_call(value):
            kwargs_clean = not any(_mentions_dangerous_name(kw.value) for kw in value.keywords)
            return _SAFE if kwargs_clean else ""
        if _is_restricted_dict_literal(value, scope):
            return _SAFE
        if isinstance(value, ast.Name) and scope.get(value.id) == _SAFE:
            return _SAFE
        if _is_plain_dict_literal(value) and not _mentions_dangerous_name(value):
            return _PLAIN_DICT
        return ""

    def _bind(self, target: ast.AST, value: ast.AST | None) -> None:
        if isinstance(target, ast.Name):
            self._scopes[-1][target.id] = self._classify(value)

    def _taint(self, name: str) -> None:
        """A tracked namespace was mutated in a way that may re-admit full builtins."""
        if name in self._scopes[-1]:
            self._scopes[-1][name] = ""

    def _note_subscript_store(self, target: ast.Subscript, value: ast.AST) -> None:
        # ns["np"] = np keeps ns restricted; ns["__builtins__"] = ..., a computed key, or a
        # dangerous value does not.
        if not isinstance(target.value, ast.Name):
            return
        key = target.slice
        benign_key = isinstance(key, ast.Constant) and key.value != "__builtins__"
        if not benign_key or _mentions_dangerous_name(value):
            self._taint(target.value.id)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                self._note_subscript_store(target, node.value)
            self._bind(target, node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.generic_visit(node)
        if isinstance(node.target, ast.Subscript):
            self._note_subscript_store(node.target, node.value)
        elif isinstance(node.target, ast.Name) and not self._merge_is_benign(node.value):
            self._taint(node.target.id)  # ns |= {...}

    @staticmethod
    def _merge_is_benign(value: ast.AST) -> bool:
        """A merged-in mapping is benign only if it is a visible dict literal that neither sets
        ``__builtins__`` nor carries a dangerous name; anything opaque might."""
        return (
            isinstance(value, ast.Dict)
            and _is_plain_dict_literal(value)
            and _builtins_entry(value) is None
            and not _mentions_dangerous_name(value)
        )

    def _note_mutating_call(self, node: ast.Call) -> None:
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)):
            return
        name = fn.value.id
        if fn.attr in {"update", "__ior__"}:
            args_benign = all(self._merge_is_benign(a) for a in node.args) and not any(
                _mentions_dangerous_name(kw.value) or kw.arg in (None, "__builtins__")
                for kw in node.keywords
            )
            if not args_benign:
                self._taint(name)
        elif fn.attr in {"setdefault", "__setitem__"}:
            key = node.args[0] if node.args else None
            benign = isinstance(key, ast.Constant) and key.value != "__builtins__"
            if not benign or any(_mentions_dangerous_name(a) for a in node.args[1:]):
                self._taint(name)

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
        self._note_mutating_call(node)
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
    # ── adversarial review of a25cc4a88: each of these escaped at runtime yet scanned clean ──
    (
        "builtins re-assigned after factory",
        "import builtins\ndef f(c):\n    ns = safe_exec_globals()\n    ns['__builtins__'] = builtins\n    exec(c, ns)\n",
        1,
    ),
    (
        "update with vars(builtins)",
        "import builtins\ndef f(c):\n    ns = safe_exec_globals()\n    ns.update(vars(builtins))\n    exec(c, ns)\n",
        1,
    ),
    (
        "in-place merge re-adds builtins",
        "import builtins\ndef f(c):\n    ns = safe_exec_globals()\n    ns |= {'__builtins__': builtins}\n    exec(c, ns)\n",
        1,
    ),
    (
        "restricted dict filled via update",
        "import builtins\ndef f(c):\n    b = {}\n    b.update(vars(builtins))\n    exec(c, {'__builtins__': b})\n",
        1,
    ),
    (
        "literal smuggles real __import__",
        "def f(c):\n    exec(c, {'__builtins__': {'__import__': __import__, 'open': open}})\n",
        1,
    ),
    (
        "dangerous module beside restricted builtins",
        "import os\ndef f(c):\n    exec(c, {'__builtins__': {}, 'os': os})\n",
        1,
    ),
    (
        "factory kwarg injects os",
        "import os\ndef f(c):\n    exec(c, safe_exec_globals(os=os))\n",
        1,
    ),
    (
        "duplicate key, last wins",
        # opaque last value `b`, NOT a dangerous name: otherwise the dangerous-name rule
        # masks a first-wins bug (a mutant flipping to first-wins survived exactly that way)
        "def f(c, b):\n    exec(c, {'__builtins__': {}, '__builtins__': b})\n",
        1,
    ),
    (
        "opaque merge taints",
        "def f(c, extra):\n    ns = safe_exec_globals()\n    ns.update(extra)\n    exec(c, ns)\n",
        1,
    ),
    # ── benign mutations must NOT taint (false positives train people to add pragmas) ──
    (
        "benign item added after factory",
        "import numpy as np\ndef f(c):\n    ns = safe_exec_globals()\n    ns['np'] = np\n    exec(c, ns)\n",
        0,
    ),
    (
        "benign literal update",
        "def f(c):\n    ns = safe_exec_globals()\n    ns.update({'k': 3})\n    exec(c, ns)\n",
        0,
    ),
    (
        "benign factory kwarg",
        "import numpy as np\ndef f(c):\n    exec(c, safe_exec_globals(np=np))\n",
        0,
    ),
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
