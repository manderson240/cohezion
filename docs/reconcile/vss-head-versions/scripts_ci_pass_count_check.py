#!/usr/bin/env python3
"""pass_count_check.py — do the "→ N passed" claims in harness.md match reality?

WHY THIS EXISTS (2026-08-19)
----------------------------
`doc_code_consistency.py` checks that documented file paths, modules, `Class.method` references
and constructor kwargs exist. It does NOT check the claimed TEST COUNTS, and that is precisely
how the MB1 phantom survived ~8 weeks:

    harness.md, MB1:  "**Verification**: `uv run pytest ... -q` → 12 passed"
    reality:          the named class existed and passed — with SIX tests, none of which
                      referenced the field MB1 claimed to verify.

A command that runs, passes, and proves nothing is the hardest false verification to catch by
reading, because everything about it looks right. The count is the tell: a claim of 12 against a
class holding 6 is a mechanical, deterministic mismatch that no human re-reads for.

WHAT IT CHECKS
  P1  the referenced test file exists
  P2  the referenced ::Class (if any) exists in that file
  P3  the claimed count matches the number of `def test_*` in that file/class

P3 is deliberately COLLECTION-based, not execution-based: counting `def test_` via AST is
instant and deterministic, where running the suite is slow and can differ by environment. It
undercounts parametrised tests — see the KNOWN LIMITATION below, which is why this is a WARNING
and this script is report-only.

Companion to doc_code_consistency.py, deliberately NOT merged into it: that one is a BLOCKING
gate in ci.yml and automerge_guard.sh, and its self-test has been broken before as a downstream
symptom of an unrelated revert. Prove this out separately before wiring anything.

Run:  python scripts/ci/pass_count_check.py             # report
      python scripts/ci/pass_count_check.py --self-test # prove it can go RED
"""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DOCS = [REPO / ".claude" / "rules" / "harness.md"]

# `pytest tests/foo.py::Klass -q` ... → 12 passed   (bold markers and arrow style vary)
CLAIM_RE = re.compile(
    r"pytest\s+(?P<target>tests/[\w/]+\.py(?:::\w+)?)"
    r"[^\n→>]*(?:→|->|=>)\s*\**(?P<count>\d+)\**\s*(?:tests?\s*)?pass",
    re.I,
)


def count_tests(path: Path, klass: str | None) -> int | None:
    """Number of `def test_*` in a file, or inside one class. None if unparseable."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return None

    def _tests_in(body: list[ast.stmt]) -> int:
        return sum(
            1
            for n in body
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name.startswith("test_")
        )

    if klass:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == klass:
                return _tests_in(node.body)
        return -1  # class named but absent — distinct from "no tests"
    total = _tests_in(tree.body)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            total += _tests_in(node.body)
    return total


def scan_text(text: str, label: str, root: Path = REPO) -> list[tuple[str, str, str]]:
    """Return (severity, target, message) for each claim that does not check out."""
    out: list[tuple[str, str, str]] = []
    for m in CLAIM_RE.finditer(text):
        target, claimed = m.group("target"), int(m.group("count"))
        fpart, _, klass = target.partition("::")
        path = root / fpart
        if not path.exists():
            out.append(("P1", target, f"{label}: test file does not exist"))
            continue
        actual = count_tests(path, klass or None)
        if actual is None:
            out.append(("P2", target, f"{label}: file could not be parsed"))
        elif actual == -1:
            out.append(("P2", target, f"{label}: class '{klass}' not found in file"))
        elif actual != claimed:
            out.append(
                ("P3", target, f"{label}: claims {claimed} passed, file defines {actual} test(s)")
            )
    return out


_GOOD = """Verification: `uv run pytest tests/x.py::TestGood -q` → 2 passed"""
_BAD_COUNT = """Verification: `uv run pytest tests/x.py::TestGood -q` → 12 passed"""
_BAD_CLASS = """Verification: `uv run pytest tests/x.py::TestMissing -q` → 2 passed"""
_BAD_FILE = """Verification: `uv run pytest tests/nope.py -q` → 2 passed"""
_FIXTURE = '''
class TestGood:
    def test_a(self): pass
    def test_b(self): pass
'''


def self_test() -> int:
    import tempfile

    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "tests").mkdir()
        (root / "tests" / "x.py").write_text(_FIXTURE)
        cases = [
            ("GOOD: claim matches the fixture", _GOOD, 0),
            ("BAD: claims 12, fixture has 2", _BAD_COUNT, 1),
            ("BAD: class does not exist", _BAD_CLASS, 1),
            ("BAD: file does not exist", _BAD_FILE, 1),
        ]
        for name, text, want in cases:
            got = len(scan_text(text, "self-test", root))
            flag = "ok  " if got == want else "FAIL"
            ok &= got == want
            print(f"  [{flag}] {name}: expected {want} finding(s), got {got}")
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    total_claims = 0
    findings: list[tuple[str, str, str]] = []
    for doc in DOCS:
        if not doc.exists():
            print(f"(skip, missing: {doc.relative_to(REPO)})")
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        total_claims += len(CLAIM_RE.findall(text))
        findings += scan_text(text, str(doc.relative_to(REPO)))

    print(f"pass-count claims examined: {total_claims}")
    print(f"claims that do not check out: {len(findings)}\n")
    for sev, target, msg in findings:
        print(f"  [{sev}] {target}\n        {msg}")
    if findings:
        print(
            "\nNOTE: P3 counts `def test_*` statically. In principle a claim ABOVE that count "
            "could be @pytest.mark.parametrize expansion, and one BELOW it could be skips or "
            "xfails — so P3 is a WARNING, not proof.\n"
            "      MEASURED 2026-08-19, both spot-checks: neither explanation applied.\n"
            "        test_riemannian_glide.py  claims 12 -> AST 4  -> actually runs 4 passed\n"
            "        test_jepa_gate.py         claims 33 -> AST 20 -> actually runs 20 passed\n"
            "      The AST count matched the real run exactly in both. Treat a mismatch as a "
            "likely-stale doc claim until shown otherwise, not as a probable false positive."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
