#!/usr/bin/env python3
"""SurrealDB HTTP scan (ratchet): every raw ``/sql`` call must check per-statement status.

Sixth sibling. dormancy: "has a consumer?"; doc-consistency: "do the docs tell the truth?";
phantom-attr: "does the attribute exist?"; lineage: "can the reflex run alone?";
false-contract: "does the producer do what its NAME promises?"; **this: "does the writer
know whether the write happened?"**

ORIGIN (2026-09-19): SurrealDB answers HTTP 200 with ``status: "ERR"`` per statement. Three
production defects that day were this one class: the vault MCP's lineage tools returned
success ids for rows that never existed (every statement ERR since they shipped); the local
inference cascade's persistence; ``journey_transition`` rows written without a declared field.
A sweep found 67 files in ``src/cohezion`` that POST to ``/sql`` and read the body with no
per-statement check, and 8 that each hand-rolled one.

MECHANISM (AST, not regex — a grep matches the comment that says "we check status"):
a file is a CANDIDATE if it contains a string constant ending in ``/sql`` AND a network call
(``urlopen``, ``.post(``, ``ClientSession``). It is CLEAN if the same file references
``checked_statements`` (the shared checker in ``cohezion.storage.surreal_http``) or contains
a comparison of a ``.get("status")``/``["status"]`` against ``"ERR"`` (legacy hand-rolled
check). Otherwise it is UNCHECKED. The gate is a RATCHET: ``BASELINE`` pins today's count;
the scan fails if the count goes UP or if a file not in the baseline appears. Shrink the
baseline as files migrate; never grow it.

Usage:
  python scripts/ci/surreal_http_scan.py --self-test
  python scripts/ci/surreal_http_scan.py            # gate
  python scripts/ci/surreal_http_scan.py --list     # print the unchecked files
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROOTS = ("src/cohezion", "cloud-vault-mcp/src")
NETWORK_CALLS = {"urlopen", "post", "ClientSession", "request"}


def _is_status_err_compare(node: ast.Compare) -> bool:
    """``x.get("status") == "ERR"`` / ``x["status"] != "ERR"`` / ``"ERR" in ...`` shapes."""
    texts = []
    for n in [node.left, *node.comparators]:
        if isinstance(n, ast.Constant) and n.value == "ERR":
            texts.append("ERR")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get":
            if n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "status":
                texts.append("status")
        elif (
            isinstance(n, ast.Subscript)
            and isinstance(n.slice, ast.Constant)
            and n.slice.value == "status"
        ):
            texts.append("status")
    return "ERR" in texts and "status" in texts


def classify(source: str) -> str:
    """'not-a-candidate' | 'clean' | 'unchecked'."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "not-a-candidate"
    hits_sql = False
    network = False
    checked = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.rstrip("/").endswith("/sql")
        ):
            hits_sql = True
        elif isinstance(node, ast.JoinedStr):
            if any(isinstance(v, ast.Constant) and "/sql" in str(v.value) for v in node.values):
                hits_sql = True
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in NETWORK_CALLS:
                network = True
            if name == "checked_statements":
                checked = True
        elif (isinstance(node, ast.Name) and node.id == "checked_statements") or (
            isinstance(node, ast.Compare) and _is_status_err_compare(node)
        ):
            checked = True
    if not (hits_sql and network):
        return "not-a-candidate"
    return "clean" if checked else "unchecked"


def scan(roots: tuple[str, ...] = ROOTS) -> tuple[list[str], int]:
    unchecked: list[str] = []
    candidates = 0
    for root in roots:
        for p in sorted((REPO_ROOT / root).rglob("*.py")):
            rel = str(p.relative_to(REPO_ROOT))
            if "/tests/" in rel or p.name.startswith("test_"):
                continue
            verdict = classify(p.read_text(errors="ignore"))
            if verdict == "not-a-candidate":
                continue
            candidates += 1
            if verdict == "unchecked":
                unchecked.append(rel)
    return unchecked, candidates


# Ratchet: today's measured count. Shrink as files migrate to checked_statements; never grow.
BASELINE_FILE = Path(__file__).resolve().parent / "surreal_http_baseline.txt"


def read_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    return {
        ln.strip()
        for ln in BASELINE_FILE.read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    }


def self_test() -> int:
    """A planted unchecked writer must read 'unchecked'; each accepted check shape must read 'clean'."""
    unchecked = 'import urllib.request\nreq = urllib.request.Request("http://localhost:8001/sql", data=b"x")\nbody = urllib.request.urlopen(req).read()\n'
    clean_shared = (
        unchecked
        + "from cohezion.storage.surreal_http import checked_statements\nchecked_statements(body)\n"
    )
    clean_legacy = unchecked + 'if body[0].get("status") == "ERR":\n    raise RuntimeError()\n'
    lie_in_comment = unchecked + "# we check status == ERR below (we do not)\n"
    cases = [
        (unchecked, "unchecked", "planted raw writer"),
        (clean_shared, "clean", "shared checker"),
        (clean_legacy, "clean", "legacy status==ERR compare"),
        (lie_in_comment, "unchecked", "comment claiming a check is not a check"),
        ("x = 1\n", "not-a-candidate", "no /sql at all"),
    ]
    bad = [(label, classify(src), want) for src, want, label in cases if classify(src) != want]
    if bad:
        for label, got, want in bad:
            print(f"SELF-TEST FAILED: {label}: got {got}, want {want}")
        return 1
    print(f"SELF-TEST OK: {len(cases)}/{len(cases)} classification fixtures.")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    unchecked, candidates = scan()
    if "--list" in sys.argv:
        for f in unchecked:
            print(f)
        print(f"\n{len(unchecked)} unchecked of {candidates} candidates")
        return 0
    if candidates == 0:
        print("SURREAL-HTTP SCAN FAILED: zero candidates — the scanner cannot see the tree.")
        return 1
    base = read_baseline()
    new = sorted(set(unchecked) - base)
    fixed = sorted(base - set(unchecked))
    print(
        f"surreal-http: {len(unchecked)} unchecked /sql writers of {candidates} candidates (baseline {len(base)})"
    )
    if new:
        print("FAILED — NEW unchecked /sql writers (route the body through checked_statements):")
        for f in new:
            print("  " + f)
        return 1
    if fixed:
        print(
            f"↓ {len(fixed)} baseline file(s) now checked — prune them from {BASELINE_FILE.name}:"
        )
        for f in fixed:
            print("  " + f)
    print("surreal-http scan OK — no new unchecked writers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
