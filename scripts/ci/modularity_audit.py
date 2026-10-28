#!/usr/bin/env python3
"""Dynamic modularity audit: what does importing each package ACTUALLY cost and couple?

Fifth sibling of lineage_scan ("can the reflex load without the LLM layer?"), dormancy_scan,
doc_code_consistency and phantom_attr_scan: **"is the package boundary real?"**

WHY: lineage_scan (2026-09-19) recorded that a static import-graph BFS reported 0 deliberative
reach for a module that in a fresh interpreter loaded torch + the executor (10.3 s, 496 MB). A
static graph is a DECLARATION of coupling; the loaded-module set is the CONSUMPTION of it. This
audit measures both and reports the gap, per top-level package of `cohezion`.

Two layers:
  static   AST over src/cohezion: every import classified as
             eager    module scope (runs at import time)
             lazy     inside a def (runs only when called)
             typing   under `if TYPE_CHECKING:` (never runs)
             dynamic  importlib.import_module("cohezion...") / __import__ with a literal
           -> package graph, Martin fan-in/fan-out/instability, strongly-connected components,
              Newman modularity Q of the package partition over the module graph.
  dynamic  `import cohezion.<pkg>` in a FRESH interpreter per package: wall ms, RSS delta,
           cohezion modules loaded, foreign packages loaded, heavy third-party loaded, errors.
           Reach that the eager static graph cannot explain = hidden coupling.

Report-only (exit 0). Usage:
  python scripts/ci/modularity_audit.py --static-only         # AST layer, no imports executed
  python scripts/ci/modularity_audit.py --json out.json       # both layers, raw data
  python scripts/ci/modularity_audit.py --self-test           # prove the classifier can go RED
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "src"
PKG_ROOT = SRC / "cohezion"
HEAVY = (
    "torch",
    "transformers",
    "sklearn",
    "pandas",
    "scipy",
    "matplotlib",
    "qiskit",
    "sentence_transformers",
    "datasets",
    "google.adk",
    "polars",
    "gymnasium",
    "fastapi",
)

# ---------------------------------------------------------------------------- static layer


def module_name(path: Path) -> str:
    rel = path.relative_to(SRC).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def top_pkg(mod: str) -> str:
    parts = mod.split(".")
    return parts[1] if len(parts) > 1 else "<root>"


def _resolve_relative(current: str, is_pkg: bool, level: int, target: str | None) -> str:
    base = current.split(".") if is_pkg else current.split(".")[:-1]
    if level > 1:
        base = base[: len(base) - (level - 1)]
    return ".".join(base + ([target] if target else []))


class _ImportVisitor(ast.NodeVisitor):
    """Collect (target_module, kind) pairs; kind in eager|lazy|typing|dynamic."""

    def __init__(self, current: str, is_pkg: bool) -> None:
        self.current, self.is_pkg = current, is_pkg
        self.func_depth = 0
        self.typing_depth = 0
        self.edges: list[tuple[str, str, int]] = []

    def _kind(self) -> str:
        if self.typing_depth:
            return "typing"
        return "lazy" if self.func_depth else "eager"

    def _visit_scope(self, node: ast.AST) -> None:
        self.func_depth += 1
        self.generic_visit(node)
        self.func_depth -= 1

    visit_FunctionDef = visit_AsyncFunctionDef = visit_Lambda = _visit_scope  # noqa: N815 -- ast.NodeVisitor dispatch names

    def visit_If(self, node: ast.If) -> None:
        t = node.test
        is_tc = (isinstance(t, ast.Name) and t.id == "TYPE_CHECKING") or (
            isinstance(t, ast.Attribute) and t.attr == "TYPE_CHECKING"
        )
        if is_tc:
            self.typing_depth += 1
            for n in node.body:
                self.visit(n)
            self.typing_depth -= 1
            for n in node.orelse:
                self.visit(n)
        else:
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            self.edges.append((a.name, self._kind(), node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = (
            _resolve_relative(self.current, self.is_pkg, node.level, node.module)
            if node.level
            else (node.module or "")
        )
        for a in node.names:
            # `from pkg import sub` may name a submodule; the resolver below picks the longest
            # existing module, so emit the candidate and let it decide.
            self.edges.append(
                (f"{mod}.{a.name}" if a.name != "*" else mod, self._kind(), node.lineno)
            )

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
        if name in ("import_module", "__import__") and node.args:
            a0 = node.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                self.edges.append((a0.value, "dynamic", node.lineno))
        self.generic_visit(node)


def collect_static(root: Path = PKG_ROOT) -> dict:
    files = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    modules = {module_name(p): p for p in files}
    raw: dict[str, list[tuple[str, str, int]]] = {}
    parse_errors: dict[str, str] = {}
    for mod, path in modules.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            parse_errors[mod] = f"line {e.lineno}: {e.msg}"
            continue
        v = _ImportVisitor(mod, path.name == "__init__.py")
        v.visit(tree)
        raw[mod] = v.edges

    def resolve(target: str) -> str | None:
        t = target
        while t:
            if t in modules:
                return t
            t = t.rpartition(".")[0]
        return None

    edges: list[dict] = []
    unresolved: list[dict] = []
    for src, lst in raw.items():
        for target, kind, line in lst:
            if not target.startswith("cohezion"):
                continue
            dst = resolve(target)
            # Falling all the way back to the root package means nothing under it matched.
            # (A missing SUBmodule of an existing package still resolves to that package and
            # is indistinguishable from `from pkg import Symbol` statically: the dynamic
            # layer is what catches those.)
            if dst is None or (dst == "cohezion" and target != "cohezion"):
                unresolved.append({"src": src, "target": target, "kind": kind, "line": line})
                continue
            if dst != src:
                edges.append({"src": src, "dst": dst, "kind": kind, "line": line})
    return {
        "modules": sorted(modules),
        "edges": edges,
        "unresolved": unresolved,
        "parse_errors": parse_errors,
        "loc": {m: _loc(p) for m, p in modules.items()},
    }


def _loc(p: Path) -> int:
    try:
        return sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def _ancestors(mod: str) -> list[str]:
    """Importing a.b.c executes a/__init__, a/b/__init__ first — implicit eager edges."""
    parts = mod.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts))]


def eager_closure(static: dict, start: str) -> set[str]:
    """Modules Python WILL execute on `import start`, per the static eager graph + parents."""
    adj: dict[str, set[str]] = defaultdict(set)
    mods = set(static["modules"])
    for e in static["edges"]:
        if e["kind"] == "eager":
            adj[e["src"]].add(e["dst"])
    for m in mods:
        for a in _ancestors(m):
            if a in mods:
                adj[m].add(a)
    seen, stack = set(), [start]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack.extend(adj[m] - seen)
    return seen


def tarjan_scc(nodes: list[str], adj: dict[str, set[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on, stack, out = set(), [], []
    counter = [0]
    sys.setrecursionlimit(max(10000, len(nodes) * 4))

    def strong(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in adj.get(v, ()):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            out.append(sorted(comp))

    for n in nodes:
        if n not in index:
            strong(n)
    return out


def newman_q(edges: list[tuple[str, str]], community: dict[str, str]) -> float:
    """Undirected Newman–Girvan modularity of a partition. Q>0.3 = meaningful structure."""
    deg: dict[str, int] = defaultdict(int)
    m = 0
    intra = 0
    seen = set()
    for a, b in edges:
        key = (a, b) if a < b else (b, a)
        if a == b or key in seen:
            continue
        seen.add(key)
        m += 1
        deg[a] += 1
        deg[b] += 1
        if community[a] == community[b]:
            intra += 1
    if m == 0:
        return 0.0
    tot: dict[str, int] = defaultdict(int)
    for n, d in deg.items():
        tot[community[n]] += d
    return intra / m - sum((t / (2 * m)) ** 2 for t in tot.values())


def package_metrics(static: dict, kinds: tuple[str, ...] = ("eager",)) -> dict:
    pkgs = sorted({top_pkg(m) for m in static["modules"]})
    out_e: dict[str, set[str]] = defaultdict(set)
    in_e: dict[str, set[str]] = defaultdict(set)
    weight: dict[tuple[str, str], int] = defaultdict(int)
    for e in static["edges"]:
        if e["kind"] not in kinds:
            continue
        a, b = top_pkg(e["src"]), top_pkg(e["dst"])
        if a == b or "<root>" in (a, b):
            continue
        out_e[a].add(b)
        in_e[b].add(a)
        weight[(a, b)] += 1
    loc: dict[str, int] = defaultdict(int)
    nmod: dict[str, int] = defaultdict(int)
    for m, n in static["loc"].items():
        loc[top_pkg(m)] += n
        nmod[top_pkg(m)] += 1
    rows = {}
    for p in pkgs:
        ce, ca = len(out_e[p]), len(in_e[p])
        rows[p] = {
            "modules": nmod[p],
            "loc": loc[p],
            "fan_out": ce,
            "fan_in": ca,
            "instability": round(ce / (ca + ce), 3) if ca + ce else None,
            "depends_on": sorted(out_e[p]),
            "used_by": sorted(in_e[p]),
        }
    sccs = [c for c in tarjan_scc(pkgs, out_e) if len(c) > 1]
    mod_edges = [(e["src"], e["dst"]) for e in static["edges"] if e["kind"] in kinds]
    q = newman_q(mod_edges, {m: top_pkg(m) for m in static["modules"]})
    mutual = sorted({tuple(sorted((a, b))) for (a, b) in weight if (b, a) in weight})
    return {
        "packages": rows,
        "sccs": sccs,
        "newman_q": round(q, 4),
        "mutual_pairs": mutual,
        "edge_weight": {f"{a}->{b}": w for (a, b), w in weight.items()},
    }


def module_sccs(static: dict) -> list[list[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for e in static["edges"]:
        if e["kind"] == "eager":
            adj[e["src"]].add(e["dst"])
    return sorted(
        (c for c in tarjan_scc(static["modules"], adj) if len(c) > 1), key=len, reverse=True
    )


# --------------------------------------------------------------------------- dynamic layer

_PROBE = r"""
import importlib, json, resource, sys, time
name, heavy = sys.argv[1], json.loads(sys.argv[2])
before = set(sys.modules)
base_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
t = time.perf_counter()
err = ""
try:
    importlib.import_module(name)
except BaseException as e:  # SystemExit from a module body counts as a finding, not a crash
    err = f"{type(e).__name__}: {e}"[:240]
ms = (time.perf_counter() - t) * 1000
rss = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - base_kb) / 1024
new = sorted(set(sys.modules) - before)
coh = [m for m in new if m == "cohezion" or m.startswith("cohezion.")]
hv = sorted({h for h in heavy for m in new if m == h or m.startswith(h + ".")})
print(json.dumps({"ms": round(ms, 1), "rss_mb": round(rss, 1), "cohezion": coh,
                  "n_third_party": len(new) - len(coh), "heavy": hv, "error": err}))
"""


def probe(name: str, python: str, timeout: int = 300) -> dict:
    env = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATH": "/usr/bin:/bin",
        "TERM": "dumb",
        "PYTHONPATH": str(SRC),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONWARNINGS": "ignore",
    }
    try:
        out = subprocess.run(
            [python, "-c", _PROBE, name, json.dumps(HEAVY)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=REPO_ROOT,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "ms": -1,
            "rss_mb": -1,
            "cohezion": [],
            "n_third_party": 0,
            "heavy": [],
            "error": f"timeout>{timeout}s",
        }
    lines = [ln for ln in out.stdout.strip().splitlines() if ln.startswith("{")]
    try:
        return dict(json.loads(lines[-1]))
    except (IndexError, json.JSONDecodeError):
        return {
            "ms": -1,
            "rss_mb": -1,
            "cohezion": [],
            "n_third_party": 0,
            "heavy": [],
            "error": f"probe crashed: {out.stderr.strip()[-240:]}",
        }


def dynamic_layer(static: dict, python: str, workers: int) -> dict:
    pkgs = sorted({top_pkg(m) for m in static["modules"]} - {"<root>"})
    targets = ["cohezion"] + [f"cohezion.{p}" for p in pkgs if f"cohezion.{p}" in static["modules"]]

    def one(t: str) -> tuple[str, dict]:
        r = probe(t, python)
        own = top_pkg(t) if t != "cohezion" else "<root>"
        loaded_pkgs = sorted({top_pkg(m) for m in r["cohezion"]} - {own, "<root>"})
        predicted = eager_closure(static, t)
        actual = set(r["cohezion"])
        r["foreign_pkgs"] = loaded_pkgs
        r["n_cohezion"] = len(actual)
        r["static_predicted"] = len(predicted)
        # Loaded but not reachable via eager static edges: dynamic/conditional coupling.
        r["unexplained"] = sorted(actual - predicted)
        # Predicted eager but not loaded: import aborted (error) or guarded by try/except.
        r["predicted_not_loaded"] = len(predicted - actual)
        del r["cohezion"]
        return t, r

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(one, targets))


# ------------------------------------------------------------------------------ self-test


def self_test() -> int:
    """The classifier must separate eager/lazy/typing/dynamic; a planted cycle must be found."""
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="modaudit_")) / "cohezion"
    (tmp / "a").mkdir(parents=True)
    (tmp / "b").mkdir()
    (tmp / "__init__.py").write_text("")
    (tmp / "a" / "__init__.py").write_text(
        "from typing import TYPE_CHECKING\nimport cohezion.b.x\n"
        "if TYPE_CHECKING:\n    import cohezion.b.y\n"
        "def f():\n    import cohezion.b.z\n"
        "import importlib\nimportlib.import_module('cohezion.b.w')\n"
    )
    (tmp / "b" / "__init__.py").write_text("from cohezion.a import *\n")  # planted pkg cycle
    for n in "xyzw":
        (tmp / "b" / f"{n}.py").write_text("")
    global SRC
    old, SRC = SRC, tmp.parent
    try:
        s = collect_static(tmp)
    finally:
        SRC = old
    kinds = {(e["dst"], e["kind"]) for e in s["edges"] if e["src"] == "cohezion.a"}
    want = {
        ("cohezion.b.x", "eager"),
        ("cohezion.b.y", "typing"),
        ("cohezion.b.z", "lazy"),
        ("cohezion.b.w", "dynamic"),
    }
    if not want <= kinds:
        print(f"SELF-TEST FAILED: classifier missed {sorted(want - kinds)}")
        return 1
    pm = package_metrics(s)
    if ["a", "b"] not in pm["sccs"]:
        print(f"SELF-TEST FAILED: planted a<->b cycle not detected: {pm['sccs']}")
        return 1
    # Removing the back edge must make the cycle disappear (the detector is not a constant).
    s["edges"] = [e for e in s["edges"] if e["src"] != "cohezion.b"]
    if package_metrics(s)["sccs"]:
        print("SELF-TEST FAILED: cycle reported after the back edge was removed")
        return 1
    print("SELF-TEST OK: eager/lazy/typing/dynamic classified; planted cycle found then cleared.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--static-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    static = collect_static()
    result = {
        "static": {k: static[k] for k in ("unresolved", "parse_errors")},
        "n_modules": len(static["modules"]),
        "edge_kinds": {
            k: sum(1 for e in static["edges"] if e["kind"] == k)
            for k in ("eager", "lazy", "typing", "dynamic")
        },
        "eager": package_metrics(static, ("eager",)),
        "all_runtime": package_metrics(static, ("eager", "lazy", "dynamic")),
        "module_sccs": module_sccs(static),
    }
    if not a.static_only:
        result["dynamic"] = dynamic_layer(static, a.python, a.workers)
    if a.json:
        a.json.write_text(json.dumps(result, indent=1, default=list))
    e = result["eager"]
    print(f"modules={result['n_modules']} edges={result['edge_kinds']}")
    print(
        f"eager package graph: Q={e['newman_q']}, SCCs={[len(c) for c in e['sccs']]}, "
        f"mutual pairs={len(e['mutual_pairs'])}"
    )
    print(f"module-level eager cycles: {[len(c) for c in result['module_sccs']][:10]}")
    if "dynamic" in result:
        d = result["dynamic"]
        errs = sum(1 for r in d.values() if r["error"])
        print(f"dynamic: {len(d)} packages probed, {errs} import errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
