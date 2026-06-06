"""Cohesion audit — LCOM4 over files >500 LOC (V-model audit item 10, report-only).

A "god object" claim must be backed by a COHESION METRIC, not just line count. This computes
LCOM4 = the number of connected components in a class's method graph, where two methods are
linked if they share an instance attribute (``self.x``) or one calls the other. LCOM4 == 1 is
cohesive (every method is reachable from every other through shared state); LCOM4 >= 2 means
the class is really N independent responsibilities sharing a namespace — a split candidate.

Report-only: prints a ranked manifest. Run: ``python scripts/audits/cohesion_audit.py``.
"""
from __future__ import annotations

import ast
import pathlib
import sys


def lcom4(cls: ast.ClassDef) -> tuple[int, int, int]:
    """Return (LCOM4 components, method count, 2nd-largest-cluster size) for a class.

    Raw LCOM4 over-counts singleton utility methods (staticmethod-style helpers that touch no
    ``self`` state) as separate "responsibilities". The honest god-object signal is the SIZE of
    the *second* cluster: a true god-object splits into two SUBSTANTIAL responsibilities, not one
    cohesive core plus a few utilities. So we also return the 2nd-largest cluster size.
    """
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    names = [m.name for m in methods]
    if len(methods) < 2:
        return 1, len(methods), 0

    touches: dict[str, set[str]] = {}
    for m in methods:
        attrs: set[str] = set()
        for node in ast.walk(m):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                attrs.add(node.attr)
        touches[m.name] = attrs

    parent = {n: n for n in names}

    def find(x: str) -> str:
        root = x
        while parent[root] != root:
            root = parent[root]
        parent[x] = root
        return root

    def union(a: str, b: str) -> None:
        parent[find(a)] = find(b)

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            shared = touches[a] & touches[b]
            if shared or b in touches[a] or a in touches[b]:
                union(a, b)

    sizes: dict[str, int] = {}
    for n in names:
        sizes[find(n)] = sizes.get(find(n), 0) + 1
    ordered = sorted(sizes.values(), reverse=True)
    second = ordered[1] if len(ordered) > 1 else 0
    return len(sizes), len(methods), second


def dump_clusters(file_path: str, class_name: str) -> int:
    """Print the disconnected method-clusters of one class (each = a split target)."""
    tree = ast.parse(pathlib.Path(file_path).read_text(errors="replace"))
    cls = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name),
        None,
    )
    if cls is None:
        print(f"class {class_name} not found in {file_path}")
        return 1
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    names = [m.name for m in methods]
    touches: dict[str, set[str]] = {}
    for m in methods:
        attrs: set[str] = set()
        for node in ast.walk(m):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
            ):
                attrs.add(node.attr)
        touches[m.name] = attrs
    parent = {n: n for n in names}

    def find(x: str) -> str:
        root = x
        while parent[root] != root:
            root = parent[root]
        parent[x] = root
        return root

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if (touches[a] & touches[b]) or b in touches[a] or a in touches[b]:
                parent[find(a)] = find(b)
    clusters: dict[str, list[str]] = {}
    for n in names:
        clusters.setdefault(find(n), []).append(n)
    print(f"{class_name}: {len(methods)} methods in {len(clusters)} disconnected clusters:")
    for i, ms in enumerate(sorted(clusters.values(), key=lambda v: -len(v)), 1):
        shown = ", ".join(ms[:8]) + ("…" if len(ms) > 8 else "")
        print(f"  cluster {i} ({len(ms)} methods): {shown}")
    return 0


def main() -> int:
    if len(sys.argv) == 3:
        return dump_clusters(sys.argv[1], sys.argv[2])
    rows = []
    for path in pathlib.Path("src/cohezion").rglob("*.py"):
        text = path.read_text(errors="replace")
        loc = text.count("\n") + 1
        if loc <= 500:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        # worst class = highest 2nd-cluster size (true split signal), then most methods
        worst = (1, 0, 0, "-")
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            comps, nmeth, second = lcom4(cls)
            if (second, nmeth) > (worst[2], worst[1]):
                worst = (comps, nmeth, second, cls.name)
        rows.append((loc, *worst, str(path).replace("src/cohezion/", "")))

    # Rank by 2nd-cluster size (real god-object signal), NOT raw LOC or raw component count.
    rows.sort(key=lambda r: (-r[3], -r[2], -r[0]))
    print(f"{len(rows)} files >500 LOC, ranked by 2nd-cluster size (true god-object signal):\n")
    print(f"{'LOC':>5} {'LCOM4':>5} {'meth':>4} {'2nd':>4}  flag       worst-class @ file")
    for loc, comps, nmeth, second, cname, fpath in rows:
        # TRUE god-object: a 2nd substantial responsibility-cluster (>=4 methods). A big LCOM4
        # with a tiny 2nd cluster is one cohesive core + utility singletons (large, NOT god).
        flag = "GOD" if second >= 4 else ("cohesive" if second <= 1 else "watch")
        print(f"{loc:>5} {comps:>5} {nmeth:>4} {second:>4}  {flag:<9} {cname} @ {fpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
