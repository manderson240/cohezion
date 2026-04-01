"""Vault Knowledge Graph — parses cortex notes to extract MOC structure.

Scans vault cortex markdown files for wikilinks ([[target]]) and YAML
frontmatter, building a directed graph of nodes and edges suitable for
the VaultKnowledgeGraph.tsx visualization component.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


logger = logging.getLogger(__name__)

# Match Obsidian-style wikilinks: [[target]] or [[target|alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

_DEFAULT_CORTEX_DIR = Path.home() / "vaults" / "cohezion-vault" / "cortex"


@dataclass(frozen=True)
class GraphNode:
    """A node in the vault knowledge graph."""

    slug: str
    title: str
    tags: tuple[str, ...]
    aspect: str
    activation: float
    stage: str
    synapse_in: int
    synapse_out: int

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "title": self.title,
            "tags": list(self.tags),
            "aspect": self.aspect,
            "activation": self.activation,
            "stage": self.stage,
            "synapse_in": self.synapse_in,
            "synapse_out": self.synapse_out,
        }


@dataclass(frozen=True)
class GraphEdge:
    """A directed edge (wikilink) in the vault knowledge graph."""

    source: str
    target: str

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target}


@dataclass
class VaultGraph:
    """Parsed vault knowledge graph with nodes and edges."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_clusters(self) -> list[dict]:
        """Group nodes by aspect (doer/thinker/knower) for cluster visualization."""
        clusters: dict[str, list[str]] = {}
        for node in self.nodes:
            clusters.setdefault(node.aspect, []).append(node.slug)
        return [
            {"aspect": aspect, "count": len(slugs), "nodes": slugs}
            for aspect, slugs in sorted(clusters.items())
        ]

    def get_tradition_subgraph(self) -> dict:
        """Extract the indigenous cosmology subgraph (tradition-related nodes)."""
        tradition_slugs = {
            n.slug
            for n in self.nodes
            if any(t in n.tags for t in ("indigenous-cosmology", "TOE", "cross-tradition"))
        }
        sub_nodes = [n for n in self.nodes if n.slug in tradition_slugs]
        sub_edges = [
            e for e in self.edges if e.source in tradition_slugs and e.target in tradition_slugs
        ]
        return {
            "nodes": [n.to_dict() for n in sub_nodes],
            "edges": [e.to_dict() for e in sub_edges],
            "node_count": len(sub_nodes),
            "edge_count": len(sub_edges),
        }

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "clusters": self.get_clusters(),
        }


def _parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        return {}


def _extract_wikilinks(content: str) -> list[str]:
    """Extract all [[wikilink]] targets from markdown content."""
    return _WIKILINK_RE.findall(content)


def _slug_from_path(path: Path) -> str:
    """Convert a file path to a slug (filename without extension)."""
    return path.stem


def parse_cortex(cortex_dir: Path | None = None) -> VaultGraph:
    """Parse all cortex markdown files into a VaultGraph.

    Parameters
    ----------
    cortex_dir : Path | None
        Directory containing cortex notes. Defaults to
        ``~/vaults/cohezion-vault/cortex/``.

    Returns
    -------
    VaultGraph
        Parsed graph with nodes and edges.
    """
    directory = cortex_dir or _DEFAULT_CORTEX_DIR

    if not directory.is_dir():
        logger.warning("Cortex directory not found: %s", directory)
        return VaultGraph()

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    known_slugs: set[str] = set()

    md_files = sorted(directory.glob("*.md"))

    # First pass: collect all slugs
    for md_file in md_files:
        known_slugs.add(_slug_from_path(md_file))

    # Second pass: parse nodes and edges
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        fm = _parse_frontmatter(content)
        slug = _slug_from_path(md_file)
        neural = fm.get("neural", {}) or {}
        tags_raw = fm.get("tags", [])
        tags = tuple(tags_raw) if isinstance(tags_raw, list) else ()

        node = GraphNode(
            slug=slug,
            title=fm.get("title", slug.replace("-", " ").title()),
            tags=tags,
            aspect=fm.get("aspect", "unknown"),
            activation=float(neural.get("activation", 0.0)),
            stage=str(neural.get("stage", "unknown")),
            synapse_in=int(neural.get("synapse_in", 0)),
            synapse_out=int(neural.get("synapse_out", 0)),
        )
        nodes.append(node)

        # Extract wikilinks as edges (only to known cortex notes)
        for target in _extract_wikilinks(content):
            if target in known_slugs and target != slug:
                edges.append(GraphEdge(source=slug, target=target))

    # Deduplicate edges
    seen: set[tuple[str, str]] = set()
    unique_edges: list[GraphEdge] = []
    for edge in edges:
        key = (edge.source, edge.target)
        if key not in seen:
            seen.add(key)
            unique_edges.append(edge)

    return VaultGraph(nodes=nodes, edges=unique_edges)


# Module-level cache
_cached_graph: VaultGraph | None = None


def get_vault_graph(force_refresh: bool = False) -> VaultGraph:
    """Get or create the cached vault graph.

    Parameters
    ----------
    force_refresh : bool
        If True, re-parse the cortex directory instead of using the cache.
    """
    global _cached_graph
    if _cached_graph is None or force_refresh:
        _cached_graph = parse_cortex()
    return _cached_graph
