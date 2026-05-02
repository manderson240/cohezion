"""Architecture Graph API.

Reads actual package structure from src/cohezion/ and builds a
nodes+edges graph for the Cockpit mode visualization.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel


architecture_router = APIRouter(tags=["architecture"])
logger = logging.getLogger(__name__)

SRC_ROOT = Path(__file__).resolve().parents[3] / "cohezion"

CATEGORY_COLORS = {
    "compound": "#00FF00",
    "swarm": "#4facfe",
    "universe": "#f093fb",
    "flume": "#F6D365",
    "api": "#00f2fe",
    "security": "#FF3B3B",
    "cache": "#C0C0C0",
    "mcp": "#0077BE",
}


class GraphNode(BaseModel):
    id: str
    label: str
    category: str
    color: str
    module_count: int


class GraphEdge(BaseModel):
    source: str
    target: str


class ArchitectureGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def _scan_packages() -> ArchitectureGraph:
    """Build graph from actual src/cohezion/ directory structure."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen_edges: set[tuple[str, str]] = set()

    if not SRC_ROOT.is_dir():
        return ArchitectureGraph(nodes=[], edges=[])

    for pkg_dir in sorted(SRC_ROOT.iterdir()):
        if not pkg_dir.is_dir() or pkg_dir.name.startswith(("_", ".")):
            continue
        init = pkg_dir / "__init__.py"
        if not init.exists():
            continue

        pkg_name = pkg_dir.name
        py_files = list(pkg_dir.glob("*.py"))
        module_count = len([f for f in py_files if f.name != "__init__.py"])

        color = CATEGORY_COLORS.get(pkg_name, "#C0C0C0")
        nodes.append(
            GraphNode(
                id=pkg_name,
                label=pkg_name.replace("_", " ").title(),
                category=pkg_name,
                color=color,
                module_count=module_count,
            )
        )

        # Scan imports for edges
        for py_file in py_files[:10]:  # Cap to avoid slow scans
            try:
                tree = ast.parse(py_file.read_text(errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                target = None
                if isinstance(node, ast.ImportFrom) and node.module:
                    parts = node.module.split(".")
                    if len(parts) >= 2 and parts[0] == "cohezion":
                        target = parts[1]
                if target and target != pkg_name and (pkg_name, target) not in seen_edges:
                    seen_edges.add((pkg_name, target))
                    edges.append(GraphEdge(source=pkg_name, target=target))

    return ArchitectureGraph(nodes=nodes, edges=edges)


# Cache the result — regenerate when explicitly requested
_cached_graph: ArchitectureGraph | None = None


@architecture_router.get("/graph", response_model=ArchitectureGraph)
async def get_architecture_graph(refresh: bool = False) -> ArchitectureGraph:
    """Return the live architecture graph (nodes = packages, edges = imports)."""
    global _cached_graph
    if _cached_graph is None or refresh:
        _cached_graph = _scan_packages()
    return _cached_graph
