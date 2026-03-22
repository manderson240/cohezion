"""Knowledge Service - Knowledge graph operations."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.core.persistence.repositories.skill_repository import Skill
from cohezion.core.persistence.repositories.universe_repository import UniverseNode


logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""

    id: str = ""
    concept: str = ""
    node_type: str = "concept"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    embedding: list[float] | None = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""

    id: str = ""
    from_node: str = ""
    to_node: str = ""
    edge_type: str = "related"
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class KnowledgeQuery:
    """A query result from the knowledge graph."""

    matched_nodes: list[KnowledgeNode]
    matched_edges: list[KnowledgeEdge]
    confidence: float
    path: list[str] = field(default_factory=list)


class KnowledgeService:
    """Service for knowledge graph operations."""

    def __init__(
        self,
        universe_repo: Any,
        skill_repo: Any,
    ):
        """
        Initialize KnowledgeService.

        Args:
            universe_repo: Universe repository instance.
            skill_repo: Skill repository instance.
        """
        self._universe_repo = universe_repo
        self._skill_repo = skill_repo

    async def add_node(self, node: KnowledgeNode) -> str:
        """Add a node to the knowledge graph.

        Args:
            node: Knowledge node to add.

        Returns:
            Node ID.
        """
        try:
            universe_node = UniverseNode(
                id=node.id,
                content=node.concept,
                embedding=node.embedding,
                node_type=f"kg_{node.node_type}",
                metadata={
                    **node.metadata,
                    "kg_concept": node.concept,
                },
            )

            return await self._universe_repo.create(universe_node)

        except Exception as e:
            logger.error(f"Failed to add knowledge node: {e}")
            raise

    async def sync_journey(self, task_file: str, plan_file: str) -> bool:
        """Synchronize the current development journey (tasks and plans) to memory.

        Args:
            task_file: Path to task.md artifact.
            plan_file: Path to implementation_plan.md artifact.

        Returns:
            True if synchronized successfully.
        """
        import os
        from datetime import datetime

        try:
            # Read artifacts
            with open(task_file) as f:
                task_content = f.read()
            with open(plan_file) as f:
                plan_content = f.read()

            # Format for MISSION_JOURNAL.md
            date_str = datetime.now().strftime("%Y-%m-%d")
            journal_entry = f"\n\n## Session Developments ({date_str})\n"
            journal_entry += (
                f"- **Targeted Mission State**: Synchronized journey from"
                f" `{os.path.basename(task_file)}` and"
                f" `{os.path.basename(plan_file)}`.\n"
            )

            # Extract key milestones (simple heuristic)
            for line in task_content.split("\n"):
                if line.strip().startswith("- [x]"):
                    milestone = line.replace("- [x]", "").strip()
                    journal_entry += f"- **Accomplishment**: {milestone}\n"

            journal_path = "src/cohezion/knowledge_graph/MISSION_JOURNAL.md"
            with open(journal_path, "a") as f:
                f.write(journal_entry)

            # Store in SurrealDB as a high-fidelity state node
            node = KnowledgeNode(
                concept=f"Journey Sync {date_str}",
                node_type="journey_snapshot",
                metadata={
                    "tasks": task_content,
                    "plan": plan_content,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            await self.add_node(node)

            logger.info(f"✅ Journey synchronized to {journal_path} and SurrealDB.")
            return True

        except Exception as e:
            logger.error(f"Failed to sync journey: {e}")
            return False

    async def add_edge(self, edge: KnowledgeEdge) -> str:
        """Add an edge to the knowledge graph.

        Args:
            edge: Knowledge edge to add.

        Returns:
            Edge ID.
        """
        try:
            edge_id = await self._universe_repo.create_relationship(
                from_id=edge.from_node,
                to_id=edge.to_node,
                relation_type=edge.edge_type,
                weight=edge.weight,
                metadata=edge.metadata,
            )

            return edge_id or edge.id

        except Exception as e:
            logger.error(f"Failed to add knowledge edge: {e}")
            raise

    async def query_concept(
        self,
        concept: str,
        limit: int = 10,
    ) -> KnowledgeQuery:
        """Query the knowledge graph for a concept.

        Args:
            concept: Concept to search for.
            limit: Maximum results.

        Returns:
            KnowledgeQuery with matches.
        """
        try:
            similar_nodes = await self._universe_repo.query_similar(
                vector=self._concept_to_vector(concept),
                limit=limit,
                node_type="kg_concept",
            )

            matched_nodes = [
                KnowledgeNode(
                    id=node.id,
                    concept=node.content,
                    node_type=node.node_type.replace("kg_", ""),
                    metadata=node.metadata,
                    created_at=node.created_at.isoformat(),
                    embedding=node.embedding,
                )
                for node in similar_nodes
            ]

            matched_edges = []

            for node in matched_nodes:
                edges = await self._universe_repo.get_relationships(
                    node.id,
                    direction="both",
                )
                matched_edges.extend(edges)

            confidence = len(matched_nodes) / limit if matched_nodes else 0.0

            return KnowledgeQuery(
                matched_nodes=matched_nodes,
                matched_edges=matched_edges,
                confidence=confidence,
                path=[n.id for n in matched_nodes],
            )

        except Exception as e:
            logger.error(f"Failed to query concept: {e}")
            return KnowledgeQuery(
                matched_nodes=[],
                matched_edges=[],
                confidence=0.0,
            )

    async def find_path(
        self,
        from_concept: str,
        to_concept: str,
        max_depth: int = 3,
    ) -> list[str]:
        """Find a path between two concepts.

        Args:
            from_concept: Starting concept.
            to_concept: Target concept.
            max_depth: Maximum search depth.

        Returns:
            List of node IDs in path.
        """
        try:
            from_nodes = await self._universe_repo.query_similar(
                vector=self._concept_to_vector(from_concept),
                limit=1,
                node_type="kg_concept",
            )

            to_nodes = await self._universe_repo.query_similar(
                vector=self._concept_to_vector(to_concept),
                limit=1,
                node_type="kg_concept",
            )

            if not from_nodes or not to_nodes:
                return []

            from_id = from_nodes[0].id
            to_id = to_nodes[0].id

            return await self._bfs_find_path(from_id, to_id, max_depth)

        except Exception as e:
            logger.error(f"Failed to find path: {e}")
            return []

    async def connect_concepts(
        self,
        from_concept: str,
        to_concept: str,
        edge_type: str,
        weight: float = 1.0,
    ) -> str:
        """Create a connection between two concepts.

        Args:
            from_concept: Source concept.
            to_concept: Target concept.
            edge_type: Type of relationship.
            weight: Relationship strength.

        Returns:
            Edge ID.
        """
        try:
            from_nodes = await self._universe_repo.query_similar(
                vector=self._concept_to_vector(from_concept),
                limit=1,
                node_type="kg_concept",
            )

            to_nodes = await self._universe_repo.query_similar(
                vector=self._concept_to_vector(to_concept),
                limit=1,
                node_type="kg_concept",
            )

            if not from_nodes or not to_nodes:
                raise ValueError("Concepts not found in knowledge graph")

            edge = KnowledgeEdge(
                from_node=from_nodes[0].id,
                to_node=to_nodes[0].id,
                edge_type=edge_type,
                weight=weight,
            )

            return await self.add_edge(edge)

        except Exception as e:
            logger.error(f"Failed to connect concepts: {e}")
            raise

    async def index_skill(self, skill: Skill) -> str:
        """Index a skill in the knowledge graph.

        Args:
            skill: Skill to index.

        Returns:
            Node ID.
        """
        try:
            node = KnowledgeNode(
                concept=skill.description,
                node_type="skill",
                metadata={
                    "name": skill.name,
                    "path": skill.path,
                    "version": skill.version,
                    "keywords": skill.keywords,
                },
            )

            return await self.add_node(node)

        except Exception as e:
            logger.error(f"Failed to index skill: {e}")
            raise

    async def find_related_skills(
        self,
        skill_name: str,
        limit: int = 5,
    ) -> list[Skill]:
        """Find skills related to a given skill.

        Args:
            skill_name: Name of reference skill.
            limit: Maximum results.

        Returns:
            List of related skills.
        """
        try:
            skill = await self._skill_repo.get_by_name(skill_name)
            if not skill:
                return []

            concept_query = await self.query_concept(
                skill.description,
                limit=limit * 2,
            )

            related_skill_names = set()
            for node in concept_query.matched_nodes:
                name = node.metadata.get("name")
                if name and name != skill_name:
                    related_skill_names.add(name)

            related_skills = []
            for name in list(related_skill_names)[:limit]:
                s = await self._skill_repo.get_by_name(name)
                if s:
                    related_skills.append(s)

            return related_skills

        except Exception as e:
            logger.error(f"Failed to find related skills: {e}")
            return []

    async def get_graph_statistics(self) -> dict[str, int]:
        """Get statistics about the knowledge graph.

        Returns:
            Dictionary with node and edge counts.
        """
        try:
            concept_count = await self._universe_repo.count(node_type="kg_concept")
            skill_count = await self._universe_repo.count(node_type="kg_skill")
            total_nodes = await self._universe_repo.count()

            return {
                "concept_nodes": concept_count,
                "skill_nodes": skill_count,
                "total_nodes": total_nodes,
            }

        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {
                "concept_nodes": 0,
                "skill_nodes": 0,
                "total_nodes": 0,
            }

    async def _bfs_find_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int,
    ) -> list[str]:
        """BFS to find path between nodes.

        Args:
            from_id: Starting node ID.
            to_id: Target node ID.
            max_depth: Maximum search depth.

        Returns:
            List of node IDs in path.
        """
        from collections import deque

        queue = deque([(from_id, [from_id])])
        visited = {from_id}

        while queue:
            current_id, path = queue.popleft()

            if current_id == to_id:
                return path

            if len(path) >= max_depth:
                continue

            edges = await self._universe_repo.get_relationships(
                current_id,
                direction="both",
            )

            for edge in edges:
                neighbor = edge.get("to") if edge.get("from") == current_id else edge.get("from")
                if neighbor and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, [*path, neighbor]))

        return []

    def _concept_to_vector(self, concept: str) -> list[float]:
        """Convert concept string to a simple vector."""
        import hashlib

        # Security: SHA-256 used for deterministic vector generation (non-security purpose)
        hash_obj = hashlib.sha256(concept.encode())
        hash_bytes = hash_obj.digest()

        vector = [float(b) / 255.0 for b in hash_bytes[:32]]

        while len(vector) < 768:
            vector.append(0.0)

        return vector[:768]
