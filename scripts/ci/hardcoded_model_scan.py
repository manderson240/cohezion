#!/usr/bin/env python3
"""Hardcoded-model scan (ratchet): request defaults must come from the fleet roster.

Seventh sibling. surreal-http: "does the writer know whether the write happened?";
**this: "does the caller know whether the model it asks for fits right now?"**

ORIGIN (2026-10-21/22): two CPU models (Gemma-4-26B, 16.9 GB; Qwen3.6-35B, 22 GB) kept
loading into lemond's cgroup until the kernel throttled every model, NPU included. Model
choices frozen into code cannot see residency or memory: ~45 references to the 26B alone,
spread across defaults, tiers and daemons. ``cohezion.inference.fleet_roles.ROSTER.select``
now allocates by role against live residency and cgroup headroom; this scan stops new
frozen choices from creeping back.

MECHANISM (AST): flags (a) a MODULE-LEVEL assignment to a name containing "MODEL" and (b) a
function parameter named ``model``/``model_id``/``model_name`` whose value is a string
literal shaped like a lemonade catalog id (``-GGUF``, ``-gguf``, ``-FLM`` suffix). Dict and
list literals (curated footprint tables, benchmark rosters) never match. RATCHET: the
baseline pins today's entries; the scan fails on any entry not in the baseline. Remove a
line when its site moves to ``ROSTER.select(role)``; never add.

Usage:
  python scripts/ci/hardcoded_model_scan.py --self-test
  python scripts/ci/hardcoded_model_scan.py            # gate
  python scripts/ci/hardcoded_model_scan.py --list     # print current findings
"""

from __future__ import annotations

import ast
import re
import sys
import tempfile
import warnings
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROOTS = ("src/cohezion",)
BASELINE = Path(__file__).with_name("hardcoded_model_baseline.txt")
_MODEL_ID = re.compile(r"^[A-Za-z0-9._:/-]+-(GGUF|gguf|FLM)$")
_PARAM_NAMES = {"model", "model_id", "model_name"}


def _is_model_literal(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(_MODEL_ID.match(node.value))
    )


def findings_in(source: str, rel: str) -> list[str]:
    """``<rel>:<name>`` for each frozen model default in one file."""
    try:
        with warnings.catch_warnings():  # other files' invalid escapes are not our finding
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source)
    except SyntaxError:
        return []
    out: list[str] = []
    for node in tree.body:  # module-level constants only
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        for t in targets:
            if isinstance(t, ast.Name) and "MODEL" in t.id.upper() and _is_model_literal(value):
                out.append(f"{rel}:{t.id}")
    for node in ast.walk(tree):  # parameter defaults, at any depth
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            pos = a.posonlyargs + a.args
            pairs = list(zip(pos[len(pos) - len(a.defaults) :], a.defaults, strict=True))
            pairs += [(arg, d) for arg, d in zip(a.kwonlyargs, a.kw_defaults, strict=True) if d]
            for arg, default in pairs:
                if arg.arg in _PARAM_NAMES and _is_model_literal(default):
                    out.append(f"{rel}:{node.name}({arg.arg})")
    return out


def scan(root: Path = REPO_ROOT) -> list[str]:
    found: list[str] = []
    for top in ROOTS:
        for path in sorted((root / top).rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            found += findings_in(path.read_text(encoding="utf-8", errors="replace"), rel)
    return found


def baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {
        line.strip()
        for line in BASELINE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def self_test() -> int:
    bad = 'DEFAULT_MODEL = "Gemma-4-26B-A4B-it-GGUF"\ndef chat(p, model="qwen3.5-4b-FLM"):\n    pass\n'
    clean = (
        'SIZES = {"Gemma-4-26B-A4B-it-GGUF": 18.1}\nDIGEST_ROLE = "interactive"\n'
        'def chat(p, model=None):\n    pass\nNAME = "Gemma-4-26B-A4B-it-GGUF"\n'
    )
    got_bad = findings_in(bad, "x.py")
    got_clean = findings_in(clean, "x.py")
    ok = got_bad == ["x.py:DEFAULT_MODEL", "x.py:chat(model)"] and got_clean == []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src/cohezion").mkdir(parents=True)
        (root / "src/cohezion/m.py").write_text(bad)
        ok = ok and len(scan(root)) == 2
    print(
        f"hardcoded-model self-test: {'PASS' if ok else 'FAIL'} (bad={got_bad}, clean={got_clean})"
    )
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    found = scan()
    if "--list" in argv:
        print("\n".join(found))
        return 0
    new = sorted(set(found) - baseline())
    if new:
        print("NEW hardcoded model defaults (resolve with fleet_roles.ROSTER.select(role)):")
        print("\n".join(f"  {n}" for n in new))
        return 1
    print(f"hardcoded-model scan: OK ({len(found)} baselined, 0 new)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
