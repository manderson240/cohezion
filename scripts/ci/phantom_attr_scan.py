#!/usr/bin/env python3
"""Phantom-attribute scan — find ``getattr(x, "<literal>", default)`` reads of a field
the target class does not define.

    python scripts/ci/phantom_attr_scan.py --self-test  # prove it can go RED before trusting GREEN
    python scripts/ci/phantom_attr_scan.py              # gate

WHY THIS EXISTS (2026-08-26)
----------------------------
The third sibling of the existing structural gates:

  * ``dormancy_scan.py``     — "does this capability have a production consumer?"
  * ``narrow_guard_scan.py`` — "can the handler catch what the body raises?"
  * THIS                     — "does the attribute this code reads actually exist?"

The defect that motivated it starved the compound loop for weeks:

    # actioner/engine.py (pre-2026-08-26)
    if not getattr(result, "success", False):
        raise RuntimeError(
            f"compound cycle failed for {item['id']}: {getattr(result, 'error', '')}"
        )

``ExecutionResult`` has NO ``error`` field — measured: 9 constructions in
compound/executor.py, 0 pass ``error=``. The real reason lives in
``metrics["error"]`` and ``output``. So EVERY failure recorded an empty reason
("compound cycle failed for <id>: ") and a fully-blocked pipeline was
indistinguishable from a slow one.

mypy cannot catch this: ``getattr`` with a string literal and a default is
deliberate dynamism, and silently returning the default is its documented
contract. That is precisely what makes the class invisible — no exception is
raised, and the caller reads "no information available" as "nothing to report".

DESIGN — curated, static, zero-import
-------------------------------------
Mirrors ``dormancy_scan``'s curated REGISTRY rather than attempting global type
inference: each entry names the consumer file, the local VARIABLE that holds the
object, and the class. Precision over recall — a scanner with false positives is
worse than none, because it trains people to ignore it. Class fields are
extracted from the AST, so this costs no ``import cohezion`` (~7 s) in CI.

Dynamic reads (``getattr(x, name, ...)`` where name is a variable) are OUT OF
SCOPE by construction and are never flagged: they cannot be resolved statically,
and flagging them would produce exactly the noise this design rejects.
"""

from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]

# Sentinel: the class accepts ANY attribute (it defines __getattr__), so no read of
# it can be phantom. Compared by identity, never by content.
ANY_ATTRIBUTE: frozenset[str] = frozenset({"<any-attribute>"})

# (consumer file, local variable holding the object, class file, class name)
REGISTRY: list[tuple[str, str, str, str]] = [
    (
        "src/cohezion/actioner/engine.py",
        "result",
        "src/cohezion/compound/executor.py",
        "ExecutionResult",
    ),
]


def class_attributes(class_file: Path, class_name: str) -> set[str] | frozenset[str] | None:
    """Statically collect attribute names defined on *class_name*.

    Covers dataclass fields (``AnnAssign``), plain class attrs (``Assign``),
    methods/properties (``FunctionDef``), and ``self.x = ...`` bound in any
    method body. Returns None when the class cannot be located — the caller
    treats that as "cannot verify" and reports it, never as "no attributes"
    (which would turn an unreadable file into a flood of false positives).
    """
    try:
        tree = ast.parse(class_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    node = classes.get(class_name)
    if node is None:
        return None

    # A class defining __getattr__ accepts ANY attribute by contract, so no read
    # of it can be phantom. Flagging one would be a false positive, and a scanner
    # that cries wolf gets ignored — which costs more than the checks it provides.
    if any(
        isinstance(c, ast.FunctionDef | ast.AsyncFunctionDef) and c.name == "__getattr__"
        for c in node.body
    ):
        return ANY_ATTRIBUTE

    # Inherited attributes count. Bases defined in the same file are resolved;
    # a base we cannot see (imported, or a generic subscript) means the field set
    # is UNKNOWABLE here — return None so the caller reports "cannot verify"
    # rather than emitting a false positive for every inherited field.
    for base in node.bases:
        if not (isinstance(base, ast.Name) and base.id in classes):
            return None

    names: set[str] = set()
    for base in node.bases:
        if not isinstance(base, ast.Name):  # pragma: no cover — the loop above guarantees this
            return None
        inherited = class_attributes(class_file, base.id)
        if inherited is None or inherited is ANY_ATTRIBUTE:
            return inherited
        names |= inherited

    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            names.add(child.target.id)
        elif isinstance(child, ast.Assign):
            names.update(t.id for t in child.targets if isinstance(t, ast.Name))
        elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(child.name)

    # self.<attr> = ... anywhere inside the class body
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Attribute)
            and isinstance(sub.value, ast.Name)
            and sub.value.id == "self"
            and isinstance(sub.ctx, ast.Store)
        ):
            names.add(sub.attr)
    return names


def literal_getattr_reads(consumer_file: Path, variable: str) -> list[tuple[str, int]]:
    """Return (attribute, lineno) for every ``getattr(<variable>, "<lit>", ...)``."""
    try:
        tree = ast.parse(consumer_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "getattr" or len(node.args) < 2:
            continue
        target, attr = node.args[0], node.args[1]
        if not (isinstance(target, ast.Name) and target.id == variable):
            continue
        # Only string LITERALS are resolvable; a variable attr name is out of scope.
        if isinstance(attr, ast.Constant) and isinstance(attr.value, str):
            found.append((attr.value, node.lineno))
    return found


def variable_is_present(consumer_file: Path, variable: str) -> bool:
    """True if *variable* appears as a Name anywhere in the consumer.

    STALENESS GUARD. The registry binds by variable NAME, so renaming the local
    (``result`` -> ``res``) would make ``literal_getattr_reads`` return nothing
    and the scan report GREEN — coverage silently lost, which is the exact
    failure class this scanner exists to catch. Found by attacking the scanner's
    own design rather than only its output.
    """
    try:
        tree = ast.parse(consumer_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    return any(isinstance(n, ast.Name) and n.id == variable for n in ast.walk(tree))


def scan(registry: list[tuple[str, str, str, str]], root: Path = REPO) -> list[str]:
    """Return one human-readable failure line per phantom read. Empty == clean."""
    failures: list[str] = []
    for consumer_rel, variable, class_rel, class_name in registry:
        consumer, class_file = root / consumer_rel, root / class_rel
        attrs = class_attributes(class_file, class_name)
        if attrs is None:
            failures.append(
                f"{consumer_rel}: cannot verify {class_name} in {class_rel} "
                f"(class not found, unparseable, or has a base class defined elsewhere). "
                f"'Cannot verify' is reported, never treated as clean."
            )
            continue
        if attrs is ANY_ATTRIBUTE:
            # The class defines __getattr__: every attribute is legal by contract,
            # so no read of it can be phantom. Skipping is correct, not a gap.
            continue
        if not variable_is_present(consumer, variable):
            failures.append(
                f"{consumer_rel}: STALE REGISTRY — variable {variable!r} no longer appears. "
                f"This entry now checks nothing; re-point it or drop it."
            )
            continue
        for attr, lineno in literal_getattr_reads(consumer, variable):
            if attr not in attrs:
                failures.append(
                    f"{consumer_rel}:{lineno}: getattr({variable}, {attr!r}, ...) — "
                    f"{class_name} has no attribute {attr!r}. The default is returned "
                    f"silently, so this read can never fail loudly."
                )
    return failures


_GREEN = """
class ExecutionResult:
    success: bool
    output: str
    metrics: dict


def consume(result):
    return getattr(result, "metrics", None)
"""

_RED = (
    _GREEN
    + """

def consume_broken(result):
    return getattr(result, "error", "")
"""
)


def self_test() -> int:
    """Discriminating: plant the REAL historical defect and require RED, then GREEN.

    A scanner that has never been observed to fail is not evidence of a clean
    tree — it is an unverified instrument (verification-depth.md).
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "mod").mkdir()
        for label, source, want_failure in (("green", _GREEN, False), ("red", _RED, True)):
            path = root / "mod" / f"{label}.py"
            path.write_text(source, encoding="utf-8")
            reg = [(f"mod/{label}.py", "result", f"mod/{label}.py", "ExecutionResult")]
            failures = scan(reg, root=root)
            if bool(failures) is not want_failure:
                verb = "flag" if want_failure else "pass"
                print(f"SELF-TEST FAILED: scanner did not {verb} the {label} fixture: {failures}")
                return 1
    print(
        "SELF-TEST OK: scanner flags getattr(result, 'error', ...) when ExecutionResult "
        "lacks it (red) and passes a real field (green)."
    )
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    failures = scan(REGISTRY)
    if failures:
        print("PHANTOM ATTRIBUTE SCAN FAILED — code reads a field its target class does not have:")
        for f in failures:
            print("  " + f)
        print(
            "\nA getattr with a default cannot report its own failure: the default is "
            "indistinguishable from a real value (verification-depth.md)."
        )
        return 1
    print(f"phantom-attr scan OK — {len(REGISTRY)} curated consumer/class pair(s) verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
