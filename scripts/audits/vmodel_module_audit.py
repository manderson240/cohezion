#!/usr/bin/env python3
"""V-Model module audit — deterministic collector.

Systems-engineering V-model audit instrument. For every top-level module under
``src/cohezion/`` it computes the *mechanizable* V-model dimensions so the loop
iterations can spend their judgment on what needs eyes (does a test actually
verify the design? what is the right wiring target?).

Dimensions collected per module (all deterministic, no LLM, no live import):
  - py file count (top-level and recursive)
  - __init__.py presence              (discoverability / structural leg)
  - max single-file LOC + offender    (300 warn / 500 hard limit, coding-standards)
  - total LOC
  - matching tests/ dir + test-file count   (V-model verification leg)
  - py_compile health (valid Python 3.11 — harness is_legal_change rule #1)
  - external importer count            (wiring / orphan signal)
  - harness structural-invariant refs  (Learning 366 structural-before-behavioral)
  - duplicate-name sibling flag        (traceability hazard — verify, never auto-delete)

Run:  uv run python scripts/audits/vmodel_module_audit.py
Writes JSON to docs/audits/vmodel_manifest.json and prints a markdown table.

Report-only. Per user directive (2026-06-05): orphans are WIRED, never deleted —
this script flags them; the report proposes the wiring target.
"""
from __future__ import annotations

import contextlib
import json
import py_compile
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "cohezion"
TESTS = REPO / "tests"
HARNESS_FILES = [
    REPO / ".claude" / "rules" / "harness.md",
    REPO / ".claude" / "rules" / "harness_check.py",
    Path.home() / ".claude" / "rules" / "harness.md",
]

SKIP = {"__pycache__"}
# Surface-similar names to verify by hand (NOT deletion candidates).
DUP_GROUPS = [
    {"datamesh", "data_mesh"},
    {"model", "models"},
    {"sandbox", "sandboxing"},
    {"simulation", "simulations"},
    {"eval", "evaluation"},
]
WARN_LOC, HARD_LOC = 300, 500


def loc(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def module_dirs() -> list[Path]:
    return sorted(
        d for d in SRC.iterdir() if d.is_dir() and d.name not in SKIP
    )


def count_external_importers(name: str) -> int:
    """Files outside the module that do `from cohezion.<name>` / `import cohezion.<name>`."""
    pat = re.compile(rf"(?:from|import)\s+cohezion\.{re.escape(name)}\b")
    own = SRC / name
    count = 0
    for root in (SRC, TESTS):
        if not root.exists():
            continue
        for f in root.rglob("*.py"):
            if own in f.parents or f == own:
                continue
            try:
                if pat.search(f.read_text(encoding="utf-8", errors="replace")):
                    count += 1
            except OSError:
                pass
    return count


def harness_refs(name: str) -> int:
    pat = re.compile(rf"cohezion\.{re.escape(name)}\b")
    n = 0
    for hf in HARNESS_FILES:
        if hf.exists():
            with contextlib.suppress(OSError):
                n += len(pat.findall(hf.read_text(encoding="utf-8", errors="replace")))
    return n


def compile_health(d: Path) -> tuple[bool, str]:
    for f in d.rglob("*.py"):
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            return False, f"{f.relative_to(SRC)}: {str(e).splitlines()[0][:80]}"
        except OSError:
            pass
    return True, ""


def dup_sibling(name: str) -> str:
    for grp in DUP_GROUPS:
        if name in grp:
            return ",".join(sorted(grp - {name}))
    return ""


def audit_module(d: Path) -> dict:
    name = d.name
    top_py = list(d.glob("*.py"))
    all_py = list(d.rglob("*.py"))
    max_loc, max_file = 0, ""
    total = 0
    for f in all_py:
        n = loc(f)
        total += n
        if n > max_loc:
            max_loc, max_file = n, str(f.relative_to(d))
    tdir = TESTS / name
    test_files = list(tdir.rglob("test_*.py")) if tdir.is_dir() else []
    ok, err = compile_health(d)
    ext = count_external_importers(name)
    return {
        "module": name,
        "py_top": len(top_py),
        "py_recursive": len(all_py),
        "has_init": (d / "__init__.py").exists(),
        "max_loc": max_loc,
        "max_file": max_file,
        "loc_flag": "HARD" if max_loc > HARD_LOC else ("warn" if max_loc > WARN_LOC else ""),
        "total_loc": total,
        "test_dir": tdir.is_dir(),
        "test_files": len(test_files),
        "compile_ok": ok,
        "compile_err": err,
        "ext_importers": ext,
        "harness_refs": harness_refs(name),
        "dup_sibling": dup_sibling(name),
        "orphan": ext == 0,
    }


def main() -> int:
    rows = [audit_module(d) for d in module_dirs()]
    out = REPO / "docs" / "audits" / "vmodel_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Markdown table to stdout
    hdr = (
        "| Module | py | init | maxLOC | tests | compile | extImp | harness | dup | orphan |\n"
        "|---|--:|:--:|--:|--:|:--:|--:|--:|---|:--:|"
    )
    print(hdr)
    for r in sorted(rows, key=lambda x: (x["ext_importers"], x["module"])):
        print(
            f"| {r['module']} | {r['py_recursive']} | "
            f"{'Y' if r['has_init'] else '**N**'} | "
            f"{r['max_loc']}{'!' if r['loc_flag']=='HARD' else ('~' if r['loc_flag']=='warn' else '')} | "
            f"{r['test_files'] if r['test_dir'] else '**0**'} | "
            f"{'ok' if r['compile_ok'] else '**FAIL**'} | "
            f"{r['ext_importers']} | {r['harness_refs']} | "
            f"{r['dup_sibling'] or '-'} | {'Y' if r['orphan'] else '-'} |"
        )
    # Summary
    n = len(rows)
    no_init = [r["module"] for r in rows if not r["has_init"]]
    no_tests = [r["module"] for r in rows if not r["test_dir"]]
    orphans = [r["module"] for r in rows if r["orphan"]]
    hard = [f"{r['module']}/{r['max_file']}({r['max_loc']})" for r in rows if r["loc_flag"] == "HARD"]
    fails = [r["module"] for r in rows if not r["compile_ok"]]
    print(f"\n**Totals:** {n} modules")
    print(f"- missing __init__.py ({len(no_init)}): {', '.join(no_init)}")
    print(f"- no test dir ({len(no_tests)}): {', '.join(no_tests)}")
    print(f"- orphans / 0 ext-importers ({len(orphans)}): {', '.join(orphans)}")
    print(f"- compile FAIL ({len(fails)}): {', '.join(fails) or 'none'}")
    print(f"- HARD LOC>500 ({len(hard)}): {', '.join(hard) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
