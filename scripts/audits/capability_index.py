#!/usr/bin/env python3
"""Capability Index generator — the anti-"built-then-forgotten" instrument.

Pathway Move 1 (vault reports/20260717-compound-pathway.md). Scans five
surfaces and emits ONE queryable manifest agents grep BEFORE writing code:

  1. Python packages under src/cohezion: public classes/functions (AST).
  2. SurrealDB tables (live census) + static writer/reader cross-references.
  3. Claude Code hooks (~/.claude/settings.json): event, matcher, command —
     hooks are invisible fleet actors (the 418-autoload warmup incident).
  4. Entry points: scripts/ subdirs + ~/cohezion-labs top-level (orphan zone).
  5. Skill stores (global, vault, repo PRIME) — names only, 4 parallel systems.

INVARIANT: outputs are GENERATED, never hand-edited. Regenerate with:
    uv run python scripts/audits/capability_index.py
Outputs: docs/capability-index/capabilities.json  (machine)
         CAPABILITIES.md                          (grep-able, repo root)

Sibling instrument: vmodel_module_audit.py (module-quality dimensions).
This file answers "WHAT EXISTS"; that one answers "is it healthy".
"""

from __future__ import annotations

import ast
import json
import re
import time
import urllib.request
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "cohezion"
OUT_JSON = REPO / "docs" / "capability-index" / "capabilities.json"
OUT_MD = REPO / "CAPABILITIES.md"
SURREAL = "http://localhost:8001/sql"
LABS = Path.home() / "cohezion-labs"
SETTINGS = Path.home() / ".claude" / "settings.json"


# ── 1. Python public surfaces ────────────────────────────────────────────────


def scan_packages() -> dict[str, dict]:
    pkgs: dict[str, dict] = {}
    for pkg in sorted(p for p in SRC.iterdir() if p.is_dir() and (p / "__init__.py").exists()):
        entry = {"files": 0, "public": {}}
        for f in sorted(pkg.rglob("*.py")):
            entry["files"] += 1
            try:
                tree = ast.parse(f.read_text(errors="replace"))
            except SyntaxError:
                continue
            names = [
                n.name
                for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and not n.name.startswith("_")
            ]
            if names:
                entry["public"][str(f.relative_to(SRC))] = names
        pkgs[pkg.name] = entry
    return pkgs


# ── 2. SurrealDB tables + writer/reader cross-refs ───────────────────────────


def scan_tables(py_files: list[Path]) -> dict[str, dict]:
    tables: dict[str, dict] = {}
    try:
        req = urllib.request.Request(
            SURREAL,
            data=b"INFO FOR DB;",
            headers={
                "surreal-ns": "cohezion", "surreal-db": "main",
                "Content-Type": "text/plain", "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            names = sorted(json.load(r)[-1]["result"]["tables"].keys())
    except Exception:  # noqa: BLE001 — index generation is best-effort per surface
        return {"_error": {"note": "SurrealDB unreachable — table scan skipped"}}
    # Static cross-reference: which source files mention each table name.
    corpus = {f: f.read_text(errors="replace") for f in py_files}
    for t in names:
        pat = re.compile(rf"\b{re.escape(t)}\b")
        refs = sorted(str(f.relative_to(REPO)) for f, txt in corpus.items() if pat.search(txt))
        tables[t] = {"referenced_by": refs, "wire_gap": not refs}
    return tables


# ── 3. Hooks ─────────────────────────────────────────────────────────────────


def scan_hooks() -> list[dict]:
    out = []
    try:
        cfg = json.loads(SETTINGS.read_text())
        for event, groups in cfg.get("hooks", {}).items():
            for g in groups:
                home = str(Path.home())
                for h in g.get("hooks", []):
                    out.append({
                        "event": event,
                        "matcher": g.get("matcher", "*"),
                        # scrub $HOME → ~ so the committed index is portable and
                        # leaks no usernames (ultrareview merged_bug_005)
                        "command": h.get("command", "")[:160].replace(home, "~"),
                    })
    except Exception:  # noqa: BLE001 — index generation is best-effort per surface
        pass
    return out


# ── 4. Entry points ──────────────────────────────────────────────────────────


def scan_entry_points() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    scripts = REPO / "scripts"
    if scripts.exists():
        out["repo_scripts"] = sorted(
            str(p.relative_to(REPO)) for p in scripts.rglob("*.py") if p.is_file()
        )[:400]
    if LABS.exists():
        out["labs_orphan_zone"] = sorted(
            p.name for p in LABS.glob("*.py")
        )
    return out


# ── 5. Skill stores ──────────────────────────────────────────────────────────


def scan_skills() -> dict[str, list[str]]:
    stores = {
        "global": Path.home() / ".claude" / "skills",
        "vault": Path.home() / "vaults" / "cohezion-vault" / "skills",
        "repo_prime": SRC / "skills",
    }
    out: dict[str, list[str]] = {}
    for name, root in stores.items():
        if not root.exists():
            continue
        if name == "repo_prime":
            out[name] = sorted(p.stem for p in root.glob("*.md"))[:300]
        else:
            out[name] = sorted(p.name for p in root.iterdir() if p.is_dir())
    return out


# ── Emit ─────────────────────────────────────────────────────────────────────


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=None,
                   help="output dir override (default: repo root + docs/capability-index)")
    args = p.parse_args()
    global OUT_JSON, OUT_MD
    if args.out:
        OUT_JSON = args.out / "capabilities.json"
        OUT_MD = args.out / "CAPABILITIES.md"
    py_files = [f for f in SRC.rglob("*.py")] + [
        f for f in (REPO / "scripts").rglob("*.py") if f.is_file()
    ]
    index = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "invariant": "GENERATED FILE — never hand-edit; regenerate via scripts/audits/capability_index.py",
        "packages": scan_packages(),
        "surreal_tables": scan_tables(py_files),
        "hooks": scan_hooks(),
        "entry_points": scan_entry_points(),
        "skill_stores": scan_skills(),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(index, indent=1))

    # Grep-able markdown: one line per capability.
    lines = [
        "# CAPABILITIES (generated — do not hand-edit; see scripts/audits/capability_index.py)",
        f"_generated {index['generated']}; grep this BEFORE building anything new_",
        "",
    ]
    for pkg, e in index["packages"].items():
        lines.append(f"pkg {pkg} ({e['files']} files)")
        # One line per file, NO truncation — this is a grep surface; a symbol
        # that falls off the list is invisible to the pre-code gate.
        for f, names in e["public"].items():
            lines.append(f"  {f}: {', '.join(names)}")
    lines.append("")
    for t, info in index["surreal_tables"].items():
        if t.startswith("_"):
            continue
        tag = "WIRE-GAP(no code refs)" if info.get("wire_gap") else f"refs={len(info['referenced_by'])}"
        lines.append(f"table {t}: {tag}")
    lines.append("")
    for h in index["hooks"]:
        lines.append(f"hook {h['event']}[{h['matcher']}]: {h['command']}")
    lines.append("")
    for store, names in index["skill_stores"].items():
        lines.append(f"skills[{store}] ({len(names)}): {', '.join(names[:40])}{' …' if len(names) > 40 else ''}")
    if index["entry_points"].get("labs_orphan_zone"):
        lines.append("")
        lines.append(f"labs orphan zone ({len(index['entry_points']['labs_orphan_zone'])}): " + ", ".join(index["entry_points"]["labs_orphan_zone"]))
    OUT_MD.write_text("\n".join(lines) + "\n")
    n_pkg = len(index["packages"])
    n_tbl = len([t for t in index["surreal_tables"] if not t.startswith("_")])
    print(f"capability index: {n_pkg} packages, {n_tbl} tables, {len(index['hooks'])} hooks → {OUT_JSON}, {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
