#!/usr/bin/env python3
"""Declared-field scan (ratchet): a dataclass persisted by a SurrealQL write must write every field.

Seventh sibling. dormancy: "has a consumer?"; doc-consistency: "do the docs tell the truth?";
phantom-attr: "does the attribute exist?"; lineage: "can the reflex run alone?"; false-contract:
"does the producer do what its NAME promises?"; surreal-http: "does the writer know whether the
write happened?"; **this: "does the writer persist what the model DECLARES?"**

ORIGIN (2026-09-19/20): ``TrajectoryPoint`` declared ``action`` since 2026-06-27 and
``_persist_to_surreal``'s CREATE never included it -- 21,635 rows, action NULL on all, no
test could see it because the statement was a string. Fixed on 0890c6763; the same class
then turned up four more times in the same statement (timestamp/source/transformation/
metadata, 420c97f98). A field that is declared, populated in memory and dropped at the
write is a false contract at the persistence boundary: readers downstream assume it exists.

MECHANISM (AST, not regex). In each module, for every ``@dataclass`` C and every function
containing a SurrealQL write literal (an f-string or constant containing ``CREATE``/``INSERT``/
``UPSERT`` (full-record verbs; ``UPDATE`` writes subsets by design) together with `` SET `` or `` CONTENT ``), collect the ``<obj>.<attr>`` attribute
references that reach the statement -- directly in its formatted values, or through local
assignments in the same function (``dims = point.dimensions.tolist()``; ``prov = f"... {point.ts}"``),
resolved transitively. The statement PERSISTS C when the referenced attribute names cover at
least ``MIN_OVERLAP`` of C's fields (so a stray ``.status`` does not bind a class); a parameter annotation names the class outright, otherwise the largest overlap wins and a tie is skipped. Missing =
C's fields not referenced. Fields named ``id`` or starting with ``_`` are ignored.

Precision over recall: a statement that builds its SET clause from a dict or a helper in
another module is NOT a candidate (nothing to bind) and is silently skipped. The gate is a
RATCHET against ``declared_field_baseline.txt``: ``path::Class`` entries with their missing
field set; a new entry, or a grown set, is red; shrink the file as writers are completed.

Usage:
  python scripts/ci/declared_field_scan.py --self-test
  python scripts/ci/declared_field_scan.py            # gate
  python scripts/ci/declared_field_scan.py --list     # print findings
  python scripts/ci/declared_field_scan.py --file F   # scan one file (oracle runs)
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROOTS = ("src/cohezion", "cloud-vault-mcp/src")
WRITE_VERBS = ("CREATE ", "INSERT ", "UPSERT ")  # UPDATE writes subsets by design
WRITE_SHAPES = (" SET ", " CONTENT ")
MIN_OVERLAP = 2
IGNORED_FIELDS = {"id"}
BASELINE_FILE = Path(__file__).resolve().parent / "declared_field_baseline.txt"


@dataclass(frozen=True)
class Finding:
    path: str
    cls: str
    line: int
    missing: tuple[str, ...]

    @property
    def key(self) -> str:
        return f"{self.path}::{self.cls}"


def _is_dataclass(node: ast.ClassDef) -> bool:
    for d in node.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
        if name == "dataclass":
            return True
    return False


def _dataclass_fields(tree: ast.Module) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_dataclass(node):
            fields = [
                s.target.id
                for s in node.body
                if isinstance(s, ast.AnnAssign)
                and isinstance(s.target, ast.Name)
                and not s.target.id.startswith("_")
                and s.target.id not in IGNORED_FIELDS
                and not (
                    isinstance(s.annotation, ast.Subscript)
                    and getattr(s.annotation.value, "id", "") == "ClassVar"
                )
            ]
            if fields:
                out[node.name] = fields
    return out


def _literal_text(node: ast.AST) -> str:
    """Concatenated constant text of a JoinedStr/Constant (formatted values contribute nothing)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
    return ""


def _is_write_literal(node: ast.AST) -> bool:
    t = _literal_text(node).upper()
    return any(v in t for v in WRITE_VERBS) and any(s in t for s in WRITE_SHAPES)


def _attr_refs(node: ast.AST) -> set[tuple[str, str]]:
    """(object-name, attribute) pairs like ``point.dimensions`` anywhere under node."""
    refs = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            refs.add((n.value.id, n.attr))
    return refs


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _findings_in_function(fn: ast.AST, classes: dict[str, list[str]], path: str) -> list[Finding]:
    # local name -> RHS node (last assignment wins; good enough for straight-line persist code)
    assigns: dict[str, ast.AST] = {}
    annotated: dict[str, str] = {}
    for a in getattr(fn, "args", None).args if hasattr(fn, "args") else []:
        ann = a.annotation
        if isinstance(ann, ast.Name):
            annotated[a.arg] = ann.id
        elif isinstance(ann, ast.Constant) and isinstance(ann.value, str):
            annotated[a.arg] = ann.value
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    assigns[t.id] = n.value
        elif (
            isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None
        ):
            assigns[n.target.id] = n.value

    def reach(node: ast.AST, seen: set[str]) -> set[tuple[str, str]]:
        refs = _attr_refs(node)
        for name in _names(node) - seen:
            if name in assigns:
                seen.add(name)
                refs |= reach(assigns[name], seen)
        return refs

    out: list[Finding] = []
    for n in ast.walk(fn):
        if not (isinstance(n, (ast.JoinedStr, ast.Constant)) and _is_write_literal(n)):
            continue
        # a write built by .format(...) or % -- resolve through the enclosing Call/BinOp is out of scope
        refs = reach(n, set())
        attrs_by_obj: dict[str, set[str]] = {}
        for obj, attr in refs:
            attrs_by_obj.setdefault(obj, set()).add(attr)
        for obj, attrs in attrs_by_obj.items():
            if obj in ("self", "cls"):
                continue
            cls = annotated.get(obj)
            if cls is None or cls not in classes:
                # largest overlap wins; a tie between two classes is ambiguous -> skip
                ranked = sorted(classes, key=lambda c: len(attrs & set(classes[c])), reverse=True)
                if not ranked or len(attrs & set(classes[ranked[0]])) < MIN_OVERLAP:
                    continue
                if len(ranked) > 1 and len(attrs & set(classes[ranked[0]])) == len(
                    attrs & set(classes[ranked[1]])
                ):
                    continue
                cls = ranked[0]
            fields = classes[cls]
            if len(attrs & set(fields)) < MIN_OVERLAP:
                continue  # annotation disambiguates; it never binds a write that names no fields
            missing = tuple(f for f in fields if f not in attrs)
            if missing:
                out.append(Finding(path, cls, n.lineno, missing))
    return out


def scan_source(source: str, path: str = "<src>") -> list[Finding]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    classes = _dataclass_fields(tree)
    if not classes:
        return []
    out: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.extend(_findings_in_function(node, classes, path))
    # one finding per (class, statement line)
    seen: set[tuple[str, int]] = set()
    uniq = []
    for f in out:
        if (f.cls, f.line) not in seen:
            seen.add((f.cls, f.line))
            uniq.append(f)
    return uniq


def scan(roots: tuple[str, ...] = ROOTS) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    files = 0
    for root in roots:
        for p in sorted((REPO_ROOT / root).rglob("*.py")):
            rel = str(p.relative_to(REPO_ROOT))
            if "/tests/" in rel or p.name.startswith("test_"):
                continue
            files += 1
            findings.extend(scan_source(p.read_text(errors="ignore"), rel))
    return findings, files


def read_baseline() -> dict[str, set[str]]:
    base: dict[str, set[str]] = {}
    if not BASELINE_FILE.exists():
        return base
    for ln in BASELINE_FILE.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        key, _, fields = ln.partition(" ")
        base[key] = set(fields.split(",")) if fields else set()
    return base


def self_test() -> int:
    """Plant the historical defect; require RED, then GREEN; indirection and comments handled."""
    model = (
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class Point:\n    dims: list\n    coherence: float\n    action: str = ''\n\n"
    )
    dropped = model + (
        "def persist(point):\n"
        '    body = f"CREATE t SET dims = {point.dims}, coherence = {point.coherence}, created = time::now();"\n'
    )
    complete = model + (
        "def persist(point):\n"
        "    action = point.action\n"  # reached through a local
        '    body = f"CREATE t SET dims = {point.dims}, coherence = {point.coherence}, action = {action};"\n'
    )
    comment_lie = dropped.replace("def persist", "# writes action too\ndef persist")
    stray = model + (
        "def other(x):\n"
        '    q = f"UPDATE t SET coherence = {x.coherence};"\n'  # one field only: no binding
    )
    cases = [
        (dropped, [("Point", ("action",))], "historical: declared field dropped from CREATE"),
        (complete, [], "all fields reach the write (one via a local)"),
        (comment_lie, [("Point", ("action",))], "a comment claiming the write is not a write"),
        (stray, [], "single-field overlap does not bind the class"),
    ]
    bad = []
    for src, want, label in cases:
        got = [(f.cls, f.missing) for f in scan_source(src)]
        if got != want:
            bad.append((label, got, want))
    if bad:
        for label, got, want in bad:
            print(f"SELF-TEST FAILED: {label}: got {got}, want {want}")
        return 1
    print(f"SELF-TEST OK: {len(cases)}/{len(cases)} fixtures.")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if "--file" in sys.argv:
        p = Path(sys.argv[sys.argv.index("--file") + 1])
        for f in scan_source(p.read_text(), str(p)):
            print(f"{f.key}:{f.line} missing {','.join(f.missing)}")
        return 0
    findings, files = scan()
    if files == 0:
        print("DECLARED-FIELD SCAN FAILED: zero files — the scanner cannot see the tree.")
        return 1
    if "--list" in sys.argv:
        for f in findings:
            print(f"{f.key}:{f.line} missing {','.join(f.missing)}")
        print(f"\n{len(findings)} finding(s) across {files} files")
        return 0
    base = read_baseline()
    current: dict[str, set[str]] = {}
    for f in findings:
        current.setdefault(f.key, set()).update(f.missing)
    new = {k: v for k, v in current.items() if k not in base}
    grown = {k: v - base[k] for k, v in current.items() if k in base and v - base[k]}
    fixed = sorted(k for k in base if k not in current)
    print(
        f"declared-field: {len(current)} class(es) with unwritten fields across {files} files (baseline {len(base)})"
    )
    if new or grown:
        print("FAILED — declared fields dropped at a write (persist them, or shrink the model):")
        for k, v in sorted(new.items()):
            print(f"  NEW   {k}: {','.join(sorted(v))}")
        for k, v in sorted(grown.items()):
            print(f"  GREW  {k}: +{','.join(sorted(v))}")
        return 1
    if fixed:
        print(
            f"↓ {len(fixed)} baseline entr{'y' if len(fixed) == 1 else 'ies'} now complete — prune from {BASELINE_FILE.name}:"
        )
        for k in fixed:
            print("  " + k)
    print("declared-field scan OK — no new dropped fields.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
