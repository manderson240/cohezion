"""Knowledge Graph Layer for Cohezion DataMesh.

Integrates SurrealDB graph capabilities with DataMesh:
- Bidirectional relationships between entities
- Graph traversal queries
- Physics-grounded entity properties
- FLUME embedding integration
- Obsidian link synchronization
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import torch


logger = logging.getLogger(__name__)


class RelationType(Enum):
    """Types of relationships in the knowledge graph."""

    # Wiki relationships
    REFERENCES = auto()
    DERIVED_FROM = auto()
    SYNTHESIZES = auto()
    CONTRADICTS = auto()

    # Physics relationships
    FLOWS_INTO = auto()
    CAUSES = auto()
    STABILIZES = auto()
    RESONATES_WITH = auto()

    # Memory relationships (MIRIX)
    EPISODIC_LINK = auto()
    SEMANTIC_ASSOCIATION = auto()
    CORE_IDENTITY = auto()
    PROCEDURAL_STEP = auto()

    # FLUME relationships
    LATENT_NEIGHBOR = auto()
    MANIFOLD_ADJACENT = auto()
    TRAJECTORY_SUCCESSOR = auto()

    # Meta relationships
    EQUIVALENT_TO = auto()
    SPECIALIZES = auto()
    GENERALIZES = auto()


@dataclass
class KnowledgeEdge:
    """Edge in the knowledge graph with physics properties."""

    edge_id: str
    source_id: str  # DataMesh entity ID
    target_id: str  # DataMesh entity ID
    relation: RelationType

    # Physics grounding
    coherence_strength: float  # 0.0 to 1.0 (HIHO = 0.5 optimal)
    spin_alignment: float  # -1 to 1 (anti-aligned to aligned)
    manifold_distance: float | None  # FLUME distance

    # Temporal
    created_at: datetime
    valid_until: datetime | None
    confidence: float

    # Provenance
    source_system: str  # 'obsidian', 'surreal', 'mirix', 'flume', 'agent'
    evidence_refs: list[str]

    # Metadata
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeNode:
    """Node in the knowledge graph representing a DataMesh entity."""

    node_id: str
    entity_id: UUID  # Links to DataMesh entity

    # Content
    label: str
    entity_type: str
    content_summary: str

    # Physics state
    coherence: float  # Current HIHO state
    spin_vector: tuple[float, float, float]  # (x, y, z) on Bloch sphere
    manifold_position: torch.Tensor | None  # 12D manifold coordinates

    # FLUME embedding
    flume_embedding: torch.Tensor | None  # 256D latent vector

    # Cross-references
    obsidian_path: str | None
    surreal_record_id: str | None
    mirix_memory_id: str | None

    # Temporal
    created_at: datetime
    updated_at: datetime

    # Graph stats
    in_degree: int = 0
    out_degree: int = 0
    centrality: float = 0.0


class KnowledgeGraphLayer:
    """Graph layer on top of DataMesh for knowledge relationships."""

    def __init__(
        self, datamesh: Any, surreal_client: Any | None = None, flume_encoder: Any | None = None
    ):
        self.datamesh = datamesh
        self.surreal = surreal_client
        self.flume = flume_encoder

        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: dict[str, KnowledgeEdge] = {}
        self._edge_index: dict[str, list[str]] = {}  # source_id -> [edge_ids]
        self._reverse_index: dict[str, list[str]] = {}  # target_id -> [edge_ids]

    async def initialize(self) -> None:
        """Initialize graph layer."""
        logger.info("Initializing knowledge graph layer...")

        # Load from SurrealDB if available
        if self.surreal:
            await self._load_from_surreal()

        logger.info(f"Loaded {len(self.nodes)} nodes, {len(self.edges)} edges")

    async def _load_from_surreal(self) -> None:
        """Load graph data from SurrealDB."""
        # Query for knowledge nodes
        nodes_result = await self.surreal.query("SELECT * FROM knowledge_node")

        for record in nodes_result:
            node = self._record_to_node(record)
            self.nodes[node.node_id] = node

        # Query for knowledge edges
        edges_result = await self.surreal.query("SELECT * FROM knowledge_edge")

        for record in edges_result:
            edge = self._record_to_edge(record)
            self.edges[edge.edge_id] = edge
            self._index_edge(edge)

    def _record_to_node(self, record: dict) -> KnowledgeNode:
        """Convert SurrealDB record to KnowledgeNode."""
        return KnowledgeNode(
            node_id=record["id"],
            entity_id=UUID(record["entity_id"]),
            label=record["label"],
            entity_type=record["entity_type"],
            content_summary=record["content_summary"],
            coherence=record.get("coherence", 0.5),
            spin_vector=tuple(record["spin_vector"])
            if "spin_vector" in record
            else (0.0, 0.0, 0.0),
            manifold_position=torch.tensor(record["manifold_position"])
            if "manifold_position" in record
            else None,
            flume_embedding=torch.tensor(record["flume_embedding"])
            if "flume_embedding" in record
            else None,
            obsidian_path=record.get("obsidian_path"),
            surreal_record_id=record["id"],
            mirix_memory_id=record.get("mirix_memory_id"),
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
        )

    def _record_to_edge(self, record: dict) -> KnowledgeEdge:
        """Convert SurrealDB record to KnowledgeEdge."""
        return KnowledgeEdge(
            edge_id=record["id"],
            source_id=record["in"],  # SurrealDB uses in/out for edges
            target_id=record["out"],
            relation=RelationType[record["relation"]],
            coherence_strength=record.get("coherence_strength", 0.5),
            spin_alignment=record.get("spin_alignment", 0.0),
            manifold_distance=record.get("manifold_distance"),
            created_at=datetime.fromisoformat(record["created_at"]),
            valid_until=datetime.fromisoformat(record["valid_until"])
            if "valid_until" in record
            else None,
            confidence=record.get("confidence", 1.0),
            source_system=record["source_system"],
            evidence_refs=record.get("evidence_refs", []),
            properties=record.get("properties", {}),
        )

    def _index_edge(self, edge: KnowledgeEdge) -> None:
        """Add edge to indexes."""
        if edge.source_id not in self._edge_index:
            self._edge_index[edge.source_id] = []
        self._edge_index[edge.source_id].append(edge.edge_id)

        if edge.target_id not in self._reverse_index:
            self._reverse_index[edge.target_id] = []
        self._reverse_index[edge.target_id].append(edge.edge_id)

    async def create_node(
        self,
        entity_id: UUID,
        label: str,
        entity_type: str,
        content: str,
        physics_context: dict[str, Any] | None = None,
    ) -> KnowledgeNode:
        """Create new knowledge graph node."""
        node_id = f"knode:{uuid4().hex[:12]}"

        # Generate FLUME embedding if available
        flume_emb = None
        if self.flume:
            flume_emb = await self.flume.encode(content)

        node = KnowledgeNode(
            node_id=node_id,
            entity_id=entity_id,
            label=label,
            entity_type=entity_type,
            content_summary=content[:500],
            coherence=physics_context.get("coherence", 0.5) if physics_context else 0.5,
            spin_vector=physics_context.get("spin", (0.0, 1.0, 0.0))
            if physics_context
            else (0.0, 1.0, 0.0),
            manifold_position=physics_context.get("manifold_pos") if physics_context else None,
            flume_embedding=flume_emb,
            obsidian_path=None,
            surreal_record_id=None,
            mirix_memory_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self.nodes[node_id] = node

        # Persist to SurrealDB
        if self.surreal:
            await self._persist_node_to_surreal(node)

        return node

    async def _persist_node_to_surreal(self, node: KnowledgeNode) -> None:
        """Persist node to SurrealDB."""
        record = {
            "id": node.node_id,
            "entity_id": str(node.entity_id),
            "label": node.label,
            "entity_type": node.entity_type,
            "content_summary": node.content_summary,
            "coherence": node.coherence,
            "spin_vector": list(node.spin_vector),
            "manifold_position": node.manifold_position.tolist()
            if node.manifold_position is not None
            else None,
            "flume_embedding": node.flume_embedding.tolist()
            if node.flume_embedding is not None
            else None,
            "created_at": node.created_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
        }

        await self.surreal.create("knowledge_node", record)
        node.surreal_record_id = node.node_id

    async def create_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relation: RelationType,
        evidence: list[str],
        physics_properties: dict[str, float] | None = None,
    ) -> KnowledgeEdge | None:
        """Create relationship between nodes."""
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            logger.warning("Cannot create edge: nodes not found")
            return None

        edge_id = f"kedge:{uuid4().hex[:12]}"

        # Calculate physics properties
        props = physics_properties or {}
        coherence = props.get("coherence_strength", 0.5)
        spin_align = props.get("spin_alignment", 0.0)

        # Calculate manifold distance if both have embeddings
        man_dist = None
        source = self.nodes[source_node_id]
        target = self.nodes[target_node_id]
        if source.flume_embedding is not None and target.flume_embedding is not None:
            man_dist = torch.dist(source.flume_embedding, target.flume_embedding).item()

        edge = KnowledgeEdge(
            edge_id=edge_id,
            source_id=source_node_id,
            target_id=target_node_id,
            relation=relation,
            coherence_strength=coherence,
            spin_alignment=spin_align,
            manifold_distance=man_dist,
            created_at=datetime.now(),
            valid_until=None,
            confidence=props.get("confidence", 1.0),
            source_system=props.get("source_system", "agent"),
            evidence_refs=evidence,
        )

        self.edges[edge_id] = edge
        self._index_edge(edge)

        # Update node degrees
        source.out_degree += 1
        target.in_degree += 1

        # Persist to SurrealDB
        if self.surreal:
            await self._persist_edge_to_surreal(edge)

        return edge

    async def _persist_edge_to_surreal(self, edge: KnowledgeEdge) -> None:
        """Persist edge to SurrealDB as graph relation."""
        sql = f"""
        RELATE {edge.source_id}->knowledge_edge->{edge.target_id}
        SET
            relation = '{edge.relation.name}',
            coherence_strength = {edge.coherence_strength},
            spin_alignment = {edge.spin_alignment},
            confidence = {edge.confidence},
            created_at = '{edge.created_at.isoformat()}',
            evidence_refs = {json.dumps(edge.evidence_refs)}
        """

        await self.surreal.query(sql)
        edge.edge_id = f"{edge.source_id}->knowledge_edge->{edge.target_id}"

    async def traverse(
        self,
        start_node_id: str,
        relation_filter: list[RelationType] | None = None,
        min_coherence: float = 0.0,
        max_hops: int = 3,
    ) -> AsyncIterator[list[KnowledgeEdge]]:
        """Traverse graph from starting node."""
        visited = set()
        current_level = [start_node_id]

        for _hop in range(max_hops):
            next_level = []
            edges_at_level = []

            for node_id in current_level:
                if node_id in visited:
                    continue
                visited.add(node_id)

                # Get outgoing edges
                for edge_id in self._edge_index.get(node_id, []):
                    edge = self.edges.get(edge_id)
                    if edge and edge.target_id not in visited:
                        # Filter by relation type
                        if relation_filter and edge.relation not in relation_filter:
                            continue
                        # Filter by coherence
                        if edge.coherence_strength < min_coherence:
                            continue
                        edges_at_level.append(edge)
                        next_level.append(edge.target_id)

            if edges_at_level:
                yield edges_at_level

            current_level = next_level
            if not current_level:
                break

    async def find_hiho_stable_neighbors(
        self, node_id: str, tolerance: float = 0.1
    ) -> list[KnowledgeNode]:
        """Find neighbors at HIHO stability (coherence ≈ 0.5)."""
        neighbors = []

        for edge_id in self._edge_index.get(node_id, []):
            edge = self.edges.get(edge_id)
            if edge:
                target = self.nodes.get(edge.target_id)
                if target and abs(target.coherence - 0.5) < tolerance:
                    neighbors.append(target)

        return neighbors

    async def calculate_centrality(self, node_id: str) -> float:
        """Calculate PageRank-style centrality for node."""
        if node_id not in self.nodes:
            return 0.0

        # Simple eigenvector centrality based on coherence-weighted edges
        centrality = 0.0
        total_weight = 0.0

        for edge_id in self._reverse_index.get(node_id, []):
            edge = self.edges.get(edge_id)
            if edge:
                weight = edge.coherence_strength * edge.confidence
                centrality += weight
                total_weight += 1.0

        if total_weight > 0:
            centrality /= total_weight

        self.nodes[node_id].centrality = centrality
        return centrality

    async def sync_with_obsidian_links(self, vault_path: Path) -> dict[str, int]:
        """Sync Obsidian [[Wiki Links]] to graph edges."""
        import re

        stats = {"created": 0, "updated": 0, "failed": 0}

        # Find all markdown files
        for md_file in vault_path.rglob("*.md"):
            content = md_file.read_text()

            # Find wiki links
            wiki_links = re.findall(r"\[\[([^\]]+)\]\]", content)

            for link_target in wiki_links:
                # Find or create nodes
                source_id = self._node_id_from_path(md_file)
                target_id = self._node_id_from_title(link_target)

                if source_id in self.nodes and target_id in self.nodes:
                    # Check if edge exists
                    existing = self._find_edge(source_id, target_id, RelationType.REFERENCES)

                    if existing:
                        stats["updated"] += 1
                    else:
                        # Create new edge
                        await self.create_edge(
                            source_id,
                            target_id,
                            RelationType.REFERENCES,
                            evidence=[str(md_file)],
                            physics_properties={
                                "coherence_strength": 0.5,  # HIHO default
                                "confidence": 0.8,
                                "source_system": "obsidian",
                            },
                        )
                        stats["created"] += 1

        return stats

    def _node_id_from_path(self, path: Path) -> str:
        """Get node ID from file path."""
        # This would need proper lookup from the bidirectional linkage manager
        for node_id, node in self.nodes.items():
            if node.obsidian_path == str(path):
                return node_id
        return ""

    def _node_id_from_title(self, title: str) -> str:
        """Get node ID from wiki title."""
        for node_id, node in self.nodes.items():
            if node.label == title:
                return node_id
        return ""

    def _find_edge(
        self, source_id: str, target_id: str, relation: RelationType
    ) -> KnowledgeEdge | None:
        """Find existing edge matching criteria."""
        for edge_id in self._edge_index.get(source_id, []):
            edge = self.edges.get(edge_id)
            if edge and edge.target_id == target_id and edge.relation == relation:
                return edge
        return None

    async def export_to_graphviz(self, output_path: Path) -> None:
        """Export graph to GraphViz DOT format for visualization."""
        lines = ["digraph CohezionKnowledgeGraph {"]

        # Nodes
        for node_id, node in self.nodes.items():
            # Color based on coherence (green=HIHO, red=unstable)
            if abs(node.coherence - 0.5) < 0.1:
                color = "green"
            elif node.coherence > 0.7:
                color = "red"
            else:
                color = "blue"

            lines.append(f'    "{node_id}" [label="{node.label}", color={color}];')

        # Edges
        for _edge_id, edge in self.edges.items():
            # Style based on relation type
            style = "solid"
            if edge.relation in [RelationType.CONTRADICTS]:
                style = "dashed"
            elif edge.relation in [RelationType.FLOWS_INTO]:
                style = "dotted"

            lines.append(
                f'    "{edge.source_id}" -> "{edge.target_id}" '
                f'[label="{edge.relation.name}", style={style}];'
            )

        lines.append("}")

        output_path.write_text("\n".join(lines))
        logger.info(f"Exported graph to {output_path}")

    async def query_subgraph(
        self, center_node_id: str, radius: int = 2, min_confidence: float = 0.5
    ) -> dict[str, Any]:
        """Extract subgraph around center node."""
        nodes = {center_node_id: self.nodes.get(center_node_id)}
        edges = []

        current_level = [center_node_id]

        for _ in range(radius):
            next_level = []

            for node_id in current_level:
                for edge_id in self._edge_index.get(node_id, []):
                    edge = self.edges.get(edge_id)
                    if edge and edge.confidence >= min_confidence:
                        edges.append(edge)
                        nodes[edge.source_id] = self.nodes.get(edge.source_id)
                        nodes[edge.target_id] = self.nodes.get(edge.target_id)
                        next_level.append(edge.target_id)

            current_level = next_level

        return {
            "nodes": {k: v for k, v in nodes.items() if v is not None},
            "edges": edges,
            "center": center_node_id,
            "radius": radius,
        }
