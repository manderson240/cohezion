#!/usr/bin/env python3
"""doc_code_consistency.py — $0 deterministic doc↔code drift linter.

Sibling to dormancy_scan.py: dormancy_scan checks whether CODE has consumers;
this checks whether the DOCS tell the truth about the code. Verifies that
concrete code references in CLAUDE.md / harness.md / nested CLAUDE.md actually
exist, catching the drift class found manually 2026-07-22 (harness.md's
`physics/fractal_metrics` when it lives in `inference/`; the journey-tracking
skill claiming `JourneyTracker.save_checkpoint` which is on LongHorizonTask).

Checks (deterministic, no LLM):
  E1 file-path : every `src/cohezion|scripts|tests/....py` path referenced exists.
  E2 module    : every backtick `cohezion.dotted.module` resolves to a file.
  W3 class.method : `ClassName.method` where ClassName is defined in src but
                    `def method` is not defined in ClassName's file -> WARN.
  W4 ctor kwarg   : `ClassName(kwarg=...)` where ClassName is defined in src but
                    `kwarg` is not a field/param/attr of it -> WARN. Added
                    2026-07-29 after RGA1/RGA2 phantoms passed W3 clean: the
                    drift was written as `Cls(kwarg=0.0)`, which CLSMETH_RE
                    cannot see (it requires `Cls.member` adjacency).
  E5 enumeration  : a nested CLAUDE.md claiming "Entry points (N modules)" where N
                    != the package's actual module count -> ERROR. Added 2026-07-31.
                    E1-E4 all verify REFERENTIAL truth ("does this name resolve?");
                    none verify ENUMERATIVE truth ("does this list claim to be
                    complete, and is it?"). data_mesh/CLAUDE.md declared 12 with 13
                    on disk while every reference in it resolved perfectly — the
                    three undocumented ones (inference_products, kanban_bridge,
                    land_runner) were the newest, load-bearing modules.
                    Compares declared vs ACTUAL, never declared vs the table's row
                    count: large packages (swarm, 74) deliberately show a truncated
                    top-N table, so a declared-vs-listed check would fire on
                    intentional truncation and get disabled within a week.

Usage:
  python scripts/ci/doc_code_consistency.py            # report + exit 1 on E-errors
  python scripts/ci/doc_code_consistency.py --report   # always exit 0 (advisory)
  python scripts/ci/doc_code_consistency.py --self-test # prove the checks can FAIL
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"

DOCS = [REPO / "CLAUDE.md", REPO / ".claude/rules/harness.md"]
DOCS += sorted(SRC.rglob("CLAUDE.md"))

FILE_RE = re.compile(r"`?((?:src/cohezion|scripts|tests)/[\w./-]+\.py)`?")
MODULE_RE = re.compile(r"`(cohezion(?:\.[A-Za-z_][\w]*)+)`")
CLSMETH_RE = re.compile(r"`([A-Z][A-Za-z0-9]+)\.([a-z_][\w]*)\(?\)?`")
CTORKW_RE = re.compile(r"`([A-Z][A-Za-z0-9]+)\(([a-z_][\w]*)\s*=")
ENTRYPOINTS_RE = re.compile(r"Entry points \((\d+) modules?\)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
TESTNAME_RE = re.compile(r"\b(Test[A-Z]\w+|test_[a-z0-9][\w]*)\b")


def _package_modules(pkg: Path) -> list[str]:
    """The modules a nested CLAUDE.md is enumerating: this package's own .py files.

    Non-recursive and `__init__.py`-excluded — the convention the existing docs already
    follow (verified: sessions 2/2, swarm 74/74 reproduce their declared counts).
    """
    return sorted(p.name for p in pkg.glob("*.py") if p.name != "__init__.py")


# false-positive stoplist for E1: paths used illustratively (globs, ellipses, placeholders)
def _looks_placeholder(p: str) -> bool:
    return any(t in p for t in ("*", "...", "<", ">", "{", "}", "__"))


def _module_to_path(mod: str) -> Path | None:
    rel = mod.split(".", 1)[1].replace(".", "/")  # drop leading 'cohezion'
    for cand in (SRC / "cohezion" / (rel + ".py"), SRC / "cohezion" / rel / "__init__.py"):
        if cand.exists():
            return cand
    # A dotted path may end in a SYMBOL rather than a module
    # (`cohezion.physics.RiemannianMetric`) — drop the last segment and resolve
    # the parent. Guarded: only when the tail plausibly names a symbol, i.e. it
    # is CapWords/UPPER_CASE, or it is actually defined in the parent module.
    # Without this guard a genuinely missing lowercase module silently resolves
    # to its package __init__ and E2 can never fire (found by --self-test,
    # 2026-07-29).
    if "/" not in rel:
        return None
    parent, tail = rel.rsplit("/", 1)
    for cand in (SRC / "cohezion" / (parent + ".py"), SRC / "cohezion" / parent / "__init__.py"):
        if not cand.exists():
            continue
        if tail[:1].isupper():  # CapWords / UPPER_CASE => a symbol, not a module
            return cand
        src = cand.read_text(errors="replace")
        if re.search(
            rf"^\s*(async def|def|class)\s+{re.escape(tail)}\b|^\s*{re.escape(tail)}\s*[:=]",
            src,
            re.M,
        ):
            return cand  # a real lowercase symbol (function/constant) in the parent
    return None


def _class_files(cls: str) -> list[Path]:
    """ALL files defining `class <cls>` (class names are not unique in this repo)."""
    return [
        p
        for p in SRC.rglob("*.py")
        if re.search(rf"^\s*class {re.escape(cls)}\b", p.read_text(errors="replace"), re.M)
    ]


def _member_defined(files: list[Path], member: str) -> bool:
    """True if `member` appears as a method OR dataclass field OR class/instance attr in ANY file."""
    pat = re.compile(
        rf"^\s*(async def|def)\s+{re.escape(member)}\b"  # method
        rf"|^\s*{re.escape(member)}\s*[:=]"  # dataclass field / class attr
        rf"|self\.{re.escape(member)}\s*=",  # instance attr
        re.M,
    )
    return any(pat.search(p.read_text(errors="replace")) for p in files)


# E6 grandfather list — phantoms known when the check landed (2026-08-14), enumerated so
# NEW phantoms fail immediately while old debt stays visible as warnings. Do NOT add to
# this list: write the test or delete the claim. (Measured fresh at port time; the
# original 2026-08-09 list shrank because TR1/MB1 were retired and LT1/RV2 gained their
# real tests in tests/compound/test_harness_claims.py in the same pick chain.)
KNOWN_PHANTOM_TESTS = frozenset(
    {
        "test_low_coherence_llm_makes_gate_skip",  # JG3
        "test_t1_epoch_fields_exist_with_zero_defaults",  # RQGM1
        "test_track_execution_action_captured_from_tier_used",  # JI1
        "test_track_execution_explicit_action_overrides_tier_used",  # JI1
    }
)


@lru_cache(maxsize=1)
def _defined_test_names() -> frozenset[str]:
    """Every pytest class/function name defined anywhere under tests/.

    Built once. It makes the "Verification:" line of every harness invariant
    checkable — the line that matters: an invariant naming a test that does not
    exist has never been verified (RTG1/RGA1/RGA2/MB1/TR1 all shipped that way).
    """
    names: set[str] = set()
    pat = re.compile(r"^\s*(?:async def|def|class)\s+((?:Test[A-Z]|test_)\w*)", re.M)
    tests_dir = REPO / "tests"
    if tests_dir.exists():
        for tp in tests_dir.rglob("*.py"):
            # MODULE stems count too: docs cite `tests/x/test_foo.py` far more often
            # than a function; ignoring stems produced 35/43 false positives.
            names.add(tp.stem)
            names.update(pat.findall(tp.read_text(errors="replace")))
    # Production helpers that merely START with "test_" are not phantoms
    # (real case: adversarial_tester.test_single_pattern, cited by AG1).
    for d in ("src", "scripts"):
        root = REPO / d
        if root.exists():
            for sp in root.rglob("*.py"):
                if "cohezion-archive" in str(sp):
                    continue
                names.update(pat.findall(sp.read_text(errors="replace")))
    return frozenset(names)


def _claimed_test_names(text: str) -> set[str]:
    """Pytest identifiers claimed inside backticks. Globs are skipped, not guessed."""
    found: set[str] = set()
    for span in BACKTICK_RE.findall(text):
        if "*" in span:  # e.g. `test_wilson_lcb_*` — a family, not a name
            continue
        found.update(TESTNAME_RE.findall(span))
    return found


def scan(docs: list[Path] | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    class_cache: dict[str, list[Path]] = {}
    for doc in docs if docs is not None else DOCS:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        try:
            rel_doc = doc.relative_to(REPO)
        except ValueError:  # --self-test scratch file outside the repo
            rel_doc = doc
        seen: set[str] = set()
        for m in FILE_RE.finditer(text):
            path = m.group(1)
            if path in seen or _looks_placeholder(path):
                continue
            seen.add(path)
            if not (REPO / path).exists():
                errors.append(f"E1 {rel_doc}: missing file `{path}`")
        for m in MODULE_RE.finditer(text):
            mod = m.group(1)
            if mod in seen:
                continue
            seen.add(mod)
            if _module_to_path(mod) is None:
                errors.append(f"E2 {rel_doc}: unresolved module `{mod}`")
        for m in CLSMETH_RE.finditer(text):
            cls, meth = m.group(1), m.group(2)
            key = f"{cls}.{meth}"
            if key in seen:
                continue
            seen.add(key)
            if cls not in class_cache:
                class_cache[cls] = _class_files(cls)
            cfs = class_cache[cls]
            if not cfs:  # unknown class — skip (too many external/generic names)
                continue
            if not _member_defined(cfs, meth):
                where = ", ".join(str(p.relative_to(REPO)) for p in cfs[:3])
                warns.append(
                    f"W3 {rel_doc}: `{cls}.{meth}` not found (method/field/attr) in {where}"
                )
        for m in CTORKW_RE.finditer(text):
            cls, kw = m.group(1), m.group(2)
            key = f"{cls}({kw}="
            if key in seen:
                continue
            seen.add(key)
            if cls not in class_cache:
                class_cache[cls] = _class_files(cls)
            cfs = class_cache[cls]
            if not cfs:  # unknown class — skip (too many external/generic names)
                continue
            if not _member_defined(cfs, kw):
                where = ", ".join(str(p.relative_to(REPO)) for p in cfs[:3])
                warns.append(f"W4 {rel_doc}: `{cls}({kw}=...)` not a field/param of {where}")
        ep = ENTRYPOINTS_RE.search(text)
        if ep:
            actual = _package_modules(doc.parent)
            declared = int(ep.group(1))
            # No `if actual` guard (D6): it silently skipped any package whose only .py is
            # __init__.py, so such a doc could declare any count and pass. The ENTRYPOINTS_RE
            # match already scopes this to docs that MAKE the claim, so a zero-module package
            # declaring a non-zero count is exactly the lie worth reporting.
            if declared != len(actual):
                listed = set(re.findall(r"^\|\s*`([\w]+\.py)`\s*\|", text, re.M))
                missing = [m for m in actual if m not in listed]
                detail = f" undocumented: {', '.join(missing)}" if missing else ""
                errors.append(
                    f"E5 {rel_doc}: declares {declared} modules, package has "
                    f"{len(actual)} (own *.py, excluding __init__.py; subpackages are NOT "
                    f"counted).{detail}"
                )
        # E6: every cited test must exist. A phantom SYMBOL and a phantom TEST NAME are
        # both invisible to the path checks above — RTG1/RGA1/RGA2/MB1/TR1 all shipped
        # citing tests defined nowhere. Only harness/CLAUDE docs make test claims.
        if doc.name in ("harness.md", "CLAUDE.md"):
            defined = _defined_test_names()
            # Burial exemption: a section whose heading says REMOVED/PHANTOM is a
            # tombstone — naming the dead test there keeps it on record so nobody
            # re-adds it. That is the opposite of claiming it as verification.
            buried: set[str] = set()
            for sec in re.split(r"(?m)^#{2,3} ", text):
                heading = sec.splitlines()[0] if sec else ""
                if "REMOVED" in heading or "PHANTOM" in heading.upper():
                    buried.update(_claimed_test_names(sec))
            live_names = _claimed_test_names(text) - buried
            for name in sorted(live_names):
                if name in defined:
                    continue
                if name in KNOWN_PHANTOM_TESTS:
                    warns.append(f"W6 {rel_doc}: known phantom test `{name}` (pre-existing debt)")
                    continue
                errors.append(
                    f"E6 {rel_doc}: cites test `{name}` which is defined nowhere — the "
                    "invariant claiming it has never been verified. Write the test or "
                    "delete the claim; do NOT add it to KNOWN_PHANTOM_TESTS."
                )
    return errors, warns


def self_test() -> int:
    """Prove the checks CAN fail — a linter that cannot fail verifies nothing."""
    import tempfile

    cases = [
        ("W4", "`RiemannianGlideTrajectory(curvature_coupling=0.0)` preserves behaviour"),
        ("W3", "`RiemannianGlideTrajectory.anisotropy_tensor()` returns ones"),
        ("E1", "see `src/cohezion/physics/does_not_exist.py` for details"),
        ("E2", "import `cohezion.physics.no_such_module` to use it"),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as td:
        for code, body in cases:
            doc = Path(td) / f"{code}.md"
            doc.write_text(body, encoding="utf-8")
            errs, warns = scan([doc])
            fired = any(x.startswith(code) for x in errs + warns)
            print(f"self-test {code}: {'PASS (fired)' if fired else 'FAIL (silent)'} — {body[:52]}")
            ok &= fired
        # E5 needs a real package on disk to count, not just a sentence.
        pkg = Path(td) / "pkg"
        pkg.mkdir()
        for name in ("__init__.py", "alpha.py", "beta.py"):
            (pkg / name).write_text("", encoding="utf-8")
        (pkg / "CLAUDE.md").write_text("## Entry points (1 module)\n", encoding="utf-8")
        errs, warns = scan([pkg / "CLAUDE.md"])
        fired = any(x.startswith("E5") for x in errs + warns)
        print(f"self-test E5: {'PASS (fired)' if fired else 'FAIL (silent)'} — declares 1, has 2")
        ok &= fired
        # E5 on a ZERO-module package (D6): before the fix the `if actual` guard skipped it,
        # so a package holding only __init__.py could declare any count and pass silently.
        empty = Path(td) / "emptypkg"
        empty.mkdir()
        (empty / "__init__.py").write_text("", encoding="utf-8")
        (empty / "CLAUDE.md").write_text("## Entry points (99 modules)\n", encoding="utf-8")
        errs, warns = scan([empty / "CLAUDE.md"])
        fired = any(x.startswith("E5") for x in errs + warns)
        print(
            f"self-test E5 zero-module: {'PASS (fired)' if fired else 'FAIL (silent)'} — declares 99, has 0"
        )
        ok &= fired
        # E5 negative control: a truthful count, and a deliberately truncated table, stay silent.
        (pkg / "CLAUDE.md").write_text(
            "## Entry points (2 modules)\n\n| Module |\n|---|\n| `alpha.py` |\n", encoding="utf-8"
        )
        errs, warns = scan([pkg / "CLAUDE.md"])
        quiet = not any(x.startswith("E5") for x in errs + warns)
        print(f"self-test E5 negative-control: {'PASS (silent)' if quiet else 'FAIL (fired)'}")
        ok &= quiet

        # E6: a phantom cited test must fire; a REAL one and a BURIED one must not.
        # Doc must be NAMED harness.md/CLAUDE.md — E6 is scoped to invariant docs.
        hdoc = Path(td) / "CLAUDE.md"
        hdoc.write_text(
            "- **Verification**: `test_this_never_existed_anywhere`\n", encoding="utf-8"
        )
        errs, warns = scan([hdoc])
        fired = any(x.startswith("E6") for x in errs)
        print(f"self-test E6: {'PASS (fired)' if fired else 'FAIL (silent)'} — phantom cited test")
        ok &= fired
        hdoc.write_text(
            "### OLD1: REMOVED — was a PHANTOM invariant\n"
            "named `test_this_never_existed_anywhere` — buried on record\n",
            encoding="utf-8",
        )
        errs, warns = scan([hdoc])
        quiet = not any(x.startswith("E6") for x in errs)
        print(f"self-test E6 burial-control: {'PASS (silent)' if quiet else 'FAIL (fired)'}")
        ok &= quiet

        # negative control: a TRUE statement must stay silent
        doc = Path(td) / "clean.md"
        doc.write_text("`RiemannianGlideTrajectory(metric=None)` is the default", encoding="utf-8")
        errs, warns = scan([doc])
        clean = not (errs + warns)
        print(
            f"self-test negative-control: {'PASS (silent)' if clean else 'FAIL: ' + str(errs + warns)}"
        )
        ok &= clean
    print("\nself-test:", "OK" if ok else "BROKEN — a check cannot fail")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    report_only = "--report" in sys.argv
    errors, warns = scan()
    for w in warns:
        print(w)
    for e in errors:
        print(e)
    print(f"\ndoc↔code: {len(errors)} error(s), {len(warns)} warning(s) across {len(DOCS)} docs")
    if errors and not report_only:
        return 1
    if not errors:
        print("doc↔code consistency OK — every file-path and module reference resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
