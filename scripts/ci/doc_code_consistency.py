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

Usage:
  python scripts/ci/doc_code_consistency.py            # report + exit 1 on E-errors
  python scripts/ci/doc_code_consistency.py --report   # always exit 0 (advisory)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"

DOCS = [REPO / "CLAUDE.md", REPO / ".claude/rules/harness.md"]
DOCS += sorted(SRC.rglob("CLAUDE.md"))

FILE_RE = re.compile(r"`?((?:src/cohezion|scripts|tests)/[\w./-]+\.py)`?")
MODULE_RE = re.compile(r"`(cohezion(?:\.[A-Za-z_][\w]*)+)`")
CLSMETH_RE = re.compile(r"`([A-Z][A-Za-z0-9]+)\.([a-z_][\w]*)\(?\)?`")

# false-positive stoplist for E1: paths used illustratively (globs, ellipses, placeholders)
def _looks_placeholder(p: str) -> bool:
    return any(t in p for t in ("*", "...", "<", ">", "{", "}", "__"))


def _module_to_path(mod: str) -> Path | None:
    rel = mod.split(".", 1)[1].replace(".", "/")  # drop leading 'cohezion'
    for cand in (SRC / "cohezion" / (rel + ".py"), SRC / "cohezion" / rel / "__init__.py"):
        if cand.exists():
            return cand
    # dotted path may end in a Symbol, not a module — try dropping the last segment
    parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
    for cand in (SRC / "cohezion" / (parent + ".py"), SRC / "cohezion" / parent / "__init__.py"):
        if parent and cand.exists():
            return cand
    return None


def _class_files(cls: str) -> list[Path]:
    """ALL files defining `class <cls>` (class names are not unique in this repo)."""
    return [p for p in SRC.rglob("*.py")
            if re.search(rf"^\s*class {re.escape(cls)}\b", p.read_text(errors="replace"), re.M)]


def _member_defined(files: list[Path], member: str) -> bool:
    """True if `member` appears as a method OR dataclass field OR class/instance attr in ANY file."""
    pat = re.compile(
        rf"^\s*(async def|def)\s+{re.escape(member)}\b"      # method
        rf"|^\s*{re.escape(member)}\s*[:=]"                    # dataclass field / class attr
        rf"|self\.{re.escape(member)}\s*=",                   # instance attr
        re.M,
    )
    return any(pat.search(p.read_text(errors="replace")) for p in files)


def scan() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    class_cache: dict[str, list[Path]] = {}
    for doc in DOCS:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        rel_doc = doc.relative_to(REPO)
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
                warns.append(f"W3 {rel_doc}: `{cls}.{meth}` not found (method/field/attr) in {where}")
    return errors, warns


def main() -> int:
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
