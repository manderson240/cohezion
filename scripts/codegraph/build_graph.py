#!/usr/bin/env python3
"""Build the codebase graph artifact so sessions don't re-derive it from scratch.

Parses src/cohezion into an imports + inherits dependency graph and writes a
compact JSON summary (spine, HITS authorities/hubs, Louvain communities, orphan
buckets) plus the git HEAD it was generated against. A session reads the JSON in
one shot instead of parsing ~1400 files; the recorded HEAD lets a staleness
check (see scripts/codegraph/codegraph-watch.sh) tell whether it needs a rebuild.

Deterministic, $0, no model. Method and findings documented in
~/vaults/cohezion-vault/reports/20260828-codebase-import-graph-map.md.

    python scripts/codegraph/build_graph.py            # write the artifact
    python scripts/codegraph/build_graph.py --print    # also print a human summary
    python scripts/codegraph/build_graph.py --dry-run  # build + summary, write nothing
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import warnings
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


try:
    import networkx as nx
except ImportError:  # optional tooling dep -- do not crash a clean checkout / CI
    sys.stderr.write(
        "build_graph.py needs networkx (analysis-only, not a runtime dep):\n"
        "    uv pip install networkx\n"
    )
    raise SystemExit(0) from None

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "cohezion"
PKG = "cohezion"
# Written to the vault so every session's vault recall can surface it.
ARTIFACT = Path.home() / "vaults" / "cohezion-vault" / "graph" / "codegraph.json"


def _module_name(path: Path) -> str:
    parts = ["cohezion", *path.relative_to(SRC).with_suffix("").parts]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _head_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def build() -> dict:
    # Sorted everywhere edges are inserted: Louvain is seeded, but its result still depends
    # on node/edge insertion order, and Python set order varies with PYTHONHASHSEED.
    files = sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)
    mods = {_module_name(p): p for p in files}
    trees: dict[str, ast.Module | None] = {}
    # ast.parse re-compiles every source file; SyntaxWarnings there (e.g. a "\|" in a
    # non-raw string) belong to the tree being analysed, not to this tool -- silence them.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        for m, p in mods.items():
            try:
                trees[m] = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                trees[m] = None

    class_def: dict[str, set[str]] = defaultdict(set)
    for m, t in trees.items():
        if t is None:
            continue
        for node in ast.walk(t):
            if isinstance(node, ast.ClassDef):
                class_def[node.name].add(m)

    def resolve(dotted: str) -> str | None:
        parts = dotted.split(".")
        while parts:
            if ".".join(parts) in mods:
                return ".".join(parts)
            parts = parts[:-1]
        return None

    def imports_of(m: str, t: ast.Module) -> set[str]:
        out: set[str] = set()
        for node in ast.walk(t):
            if isinstance(node, ast.Import):
                out |= {a.name for a in node.names if a.name.startswith(PKG)}
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = m.rsplit(".", node.level)[0] if "." in m else PKG
                    out.add(f"{base}.{node.module}" if node.module else base)
                elif node.module and node.module.startswith(PKG):
                    out.add(node.module)
        return {r for imp in out if (r := resolve(imp)) and r != m}

    def base_names(t: ast.Module) -> set[str]:
        out: set[str] = set()
        for node in ast.walk(t):
            if isinstance(node, ast.ClassDef):
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        out.add(b.id)
                    elif isinstance(b, ast.Attribute):
                        out.add(b.attr)
        return out

    g = nx.DiGraph()
    g.add_nodes_from(mods)
    inh = nx.DiGraph()
    for m, t in trees.items():
        if t is None:
            continue
        for tgt in sorted(imports_of(m, t)):
            g.add_edge(m, tgt)
        for bn in sorted(base_names(t)):
            for definer in sorted(class_def.get(bn, ())):
                if definer != m:
                    g.add_edge(m, definer)
                    inh.add_edge(m, definer)

    indeg = dict(g.in_degree())
    outdeg = dict(g.out_degree())
    try:
        hubs, auth = nx.hits(g, max_iter=500)
    except Exception:
        hubs, auth = {}, {}
    undirected = g.to_undirected()
    comms = sorted(nx.community.louvain_communities(undirected, seed=1), key=len, reverse=True)

    def top(d: dict, n: int) -> list[list]:
        return [
            [k, round(v, 5) if isinstance(v, float) else v]
            for k, v in sorted(d.items(), key=lambda x: -x[1])[:n]
        ]

    isolated = [m for m in mods if indeg[m] == 0 and outdeg[m] == 0]

    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "head_sha": _head_sha(),
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "inherit_edges": inh.number_of_edges(),
        "import_spine": top(indeg, 15),
        "orchestrators": top(outdeg, 12),
        "authorities": top(auth, 12),
        "hubs": top(hubs, 10),
        "abstraction_spine": top(dict(inh.in_degree()), 10),
        "communities": {
            "count": len(comms),
            "modularity": round(nx.community.modularity(undirected, comms), 3),
            "largest": [
                {
                    "size": len(c),
                    "packages": Counter(
                        n.split(".")[1] for n in c if n.count(".") >= 1
                    ).most_common(3),
                }
                for c in comms[:8]
            ],
        },
        "isolated_count": len(isolated),
        "subsystems": Counter(m.split(".")[1] for m in mods if m.count(".") >= 1).most_common(18),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build_graph.py",
        description=(
            "Build the cohezion import+inherits graph artifact "
            f"(written to {ARTIFACT}) so sessions read it instead of re-parsing src/."
        ),
    )
    parser.add_argument(
        "--print",
        dest="print_summary",
        action="store_true",
        help="after writing the artifact, also print a short human summary",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build and print the summary but write NOTHING (never touches the artifact)",
    )
    # argparse handles -h/--help itself and exits 0 before build() is ever reached.
    return parser.parse_args(argv)


def _print_summary(art: dict) -> None:
    print(f"spine: {', '.join(k for k, _ in art['import_spine'][:6])}")
    print(f"heart (top authority): {art['authorities'][0][0] if art['authorities'] else '?'}")
    print(
        f"communities: {art['communities']['count']} @ modularity {art['communities']['modularity']}"
    )
    print(f"isolated: {art['isolated_count']} of {art['nodes']} modules")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    art = build()
    if args.dry_run:
        print(
            f"dry-run: {art['nodes']} nodes, {art['edges']} edges, HEAD {art['head_sha'][:9]} "
            f"(not written to {ARTIFACT})"
        )
        _print_summary(art)
        return 0
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(art, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {ARTIFACT}  ({art['nodes']} nodes, {art['edges']} edges, HEAD {art['head_sha'][:9]})"
    )
    if args.print_summary:
        print()
        _print_summary(art)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
