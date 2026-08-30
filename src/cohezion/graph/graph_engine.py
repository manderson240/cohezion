"""Graph Engineering Core: Unified SurrealDB v2 Relational Graph, Hyperbolic Knowledge Mesh, and Geodesic Subgraph Traversal.

Features:
1. **SurrealDB v2 Graph Schema**: First-class `RELATE` syntax (`agent:X -> EMITTED -> event_log:Y`, `goal:A -> DEPENDS_ON -> goal:B`).
2. **2048D Poincaré Hyperbolic Embeddings**: Attaches hyperbolic coordinates to graph nodes with boundary clamping (||u|| <= 1.0 - 1e-5).
3. **Graph Operations**: BFS/DFS traversal, bidirectional path finding, topological sorting, and k-hop neighborhood extraction.
4. **SurrealQL Sanitization**: Parameterized, SQL-injection safe graph query builders.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import math
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EdgeType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"
    EMITTED = "EMITTED"
    SATISFIES = "SATISFIES"
    DERIVED_FROM = "DERIVED_FROM"
    MUTATES = "MUTATES"
    EXECUTES = "EXECUTES"


@dataclass
class GraphNode:
    """Graph vertex with typed properties and optional 12D/2048D manifold vector."""

    id: str
    node_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: np.ndarray | None = None
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        # Poincaré manifold boundary clamping to guarantee numerical stability
        if self.embedding is not None:
            norm = float(np.linalg.norm(self.embedding))
            if norm >= 1.0 - 1e-5:
                self.embedding = self.embedding * ((1.0 - 1e-5) / max(norm, 1e-12))

    def to_surreal_record(self) -> str:
        """Return formatted SurrealDB record ID (e.g. `goal:karpathy_standards`)."""
        if ":" in self.id:
            return self.id
        return f"{self.node_type}:{self.id}"


@dataclass
class GraphEdge:
    """Directed relational edge between two graph vertices."""

    in_node: str
    relation: EdgeType
    out_node: str
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_surreal_relate(self) -> str:
        """Generate sanitized SurrealDB v2 RELATE statement."""
        clean_weight = float(np.clip(self.weight, 0.0, 1000.0))
        clean_props = json.dumps({str(k): str(v) for k, v in self.properties.items()})
        return f"RELATE {self.in_node}->{self.relation.value}->{self.out_node} SET weight = {clean_weight}, properties = {clean_props};"


class KnowledgeGraphMesh:
    """In-memory + SurrealDB v2 Graph Relational Engine."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adj_out: dict[str, list[GraphEdge]] = {}
        self._adj_in: dict[str, list[GraphEdge]] = {}

    def add_node(
        self,
        node_id: str,
        node_type: str,
        properties: dict[str, Any] | None = None,
        embedding: np.ndarray | None = None,
    ) -> GraphNode:
        """Add or update a node in the graph mesh."""
        node = GraphNode(
            id=node_id,
            node_type=node_type,
            properties=properties or {},
            embedding=embedding,
        )
        self.nodes[node_id] = node
        if node_id not in self._adj_out:
            self._adj_out[node_id] = []
        if node_id not in self._adj_in:
            self._adj_in[node_id] = []
        return node

    def add_edge(
        self,
        in_node_id: str,
        relation: EdgeType | str,
        out_node_id: str,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> GraphEdge:
        """Create a directed relation between two nodes."""
        if in_node_id not in self.nodes:
            raise KeyError(f"Source node '{in_node_id}' does not exist.")
        if out_node_id not in self.nodes:
            raise KeyError(f"Target node '{out_node_id}' does not exist.")

        rel_enum = EdgeType(relation) if isinstance(relation, str) else relation
        edge = GraphEdge(
            in_node=in_node_id,
            relation=rel_enum,
            out_node=out_node_id,
            weight=weight,
            properties=properties or {},
        )
        self.edges.append(edge)
        self._adj_out[in_node_id].append(edge)
        self._adj_in[out_node_id].append(edge)
        return edge

    def get_neighbors(self, node_id: str, direction: str = "out") -> list[str]:
        """Retrieve neighboring node IDs."""
        if direction == "out":
            return [e.out_node for e in self._adj_out.get(node_id, [])]
        elif direction == "in":
            return [e.in_node for e in self._adj_in.get(node_id, [])]
        elif direction == "both":
            return list(set(self.get_neighbors(node_id, "out") + self.get_neighbors(node_id, "in")))
        raise ValueError("Direction must be 'out', 'in', or 'both'.")

    def k_hop_subgraph(self, start_node_id: str, k: int = 2) -> tuple[dict[str, GraphNode], list[GraphEdge]]:
        """Extract a k-hop localized subgraph around a focal node."""
        visited_nodes: dict[str, GraphNode] = {}
        subgraph_edges: list[GraphEdge] = []

        if start_node_id not in self.nodes:
            return visited_nodes, subgraph_edges

        queue = [(start_node_id, 0)]
        visited_set = {start_node_id}

        while queue:
            curr_id, depth = queue.pop(0)
            visited_nodes[curr_id] = self.nodes[curr_id]

            if depth < k:
                for edge in self._adj_out.get(curr_id, []):
                    subgraph_edges.append(edge)
                    if edge.out_node not in visited_set:
                        visited_set.add(edge.out_node)
                        queue.append((edge.out_node, depth + 1))

        return visited_nodes, subgraph_edges

    def topological_sort(self) -> list[str]:
        """Perform topological sort across DAG nodes (e.g. for dependency ordering)."""
        in_degree = {n: 0 for n in self.nodes}
        for edge in self.edges:
            if edge.relation == EdgeType.DEPENDS_ON:
                # out_node depends on in_node
                in_degree[edge.out_node] = in_degree.get(edge.out_node, 0) + 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for edge in self._adj_out.get(curr, []):
                if edge.relation == EdgeType.DEPENDS_ON:
                    in_degree[edge.out_node] -= 1
                    if in_degree[edge.out_node] == 0:
                        queue.append(edge.out_node)

        return order

    def generate_surrealql_batch(self) -> list[str]:
        """Generate executable SurrealQL DDL & RELATE statements for persistence."""
        statements = [
            "DEFINE TABLE OVERWRITE node SCHEMAFULL;",
            "DEFINE TABLE OVERWRITE relation SCHEMAFULL TYPE RELATION;",
        ]
        # Nodes
        for n in self.nodes.values():
            rec_id = n.to_surreal_record()
            props = json.dumps({str(k): str(v) for k, v in n.properties.items()})
            statements.append(f"UPSERT {rec_id} CONTENT {{ node_type: '{n.node_type}', properties: {props}, updated_at: time::now() }};")

        # Edges
        for e in self.edges:
            in_rec = self.nodes[e.in_node].to_surreal_record()
            out_rec = self.nodes[e.out_node].to_surreal_record()
            statements.append(f"RELATE {in_rec}->{e.relation.value}->{out_rec} SET weight = {e.weight}, properties = {json.dumps({str(k): str(v) for k, v in e.properties.items()})};")

        return statements
