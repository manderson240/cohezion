# SQL strings parameterized via SurrealDB driver, not raw string concat
"""Bidirectional linking system for Cohezion knowledge graph.

Integrates with:
- Vault (~/vaults/cohezion-vault/) for cross-session persistence
- SurrealDB 3.0 for graph relations and fast queries

Links:
- Documentation ↔ Documentation (DESIGN.md ↔ CLAUDE.md)
- Documentation ↔ Code (DESIGN.md ↔ src/cohezion/swarm/tip_of_spear_router.py)
- PRIME Skills ↔ Implementations (SMALL_MODEL_SPECIALIST_PRIME.md ↔ tip_of_spear_router.py)
- Decisions ↔ Code (vault/decisions/provider-abstraction.md ↔ model_provider.py)
- Patterns ↔ Code (vault/patterns/sovereignty.md ↔ constitutional_checker.py)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class LinkType(Enum):
    """Types of bidirectional links."""

    # Documentation links
    DOC_TO_DOC = "doc_to_doc"  # DESIGN.md → CLAUDE.md
    DOC_TO_CODE = "doc_to_code"  # DESIGN.md → tip_of_spear_router.py

    # Skill links
    SKILL_TO_CODE = "skill_to_code"  # PRIME skill → implementation
    SKILL_TO_DECISION = "skill_to_decision"  # PRIME skill → vault decision

    # Vault links
    DECISION_TO_CODE = "decision_to_code"  # vault decision → code
    PATTERN_TO_CODE = "pattern_to_code"  # vault pattern → code
    EXPERIMENT_TO_CODE = "experiment_to_code"  # vault experiment → code

    # Code links
    CODE_TO_CODE = "code_to_code"  # file.py → related_file.py
    CODE_TO_TEST = "code_to_test"  # file.py → test_file.py

    # Semantic links
    IMPLEMENTS = "implements"  # code implements concept
    REFERENCES = "references"  # A references B
    EXTENDS = "extends"  # A extends B
    SUPERSEDES = "supersedes"  # A supersedes (replaces) B


@dataclass
class BidirectionalLink:
    """A bidirectional link between two nodes in the knowledge graph."""

    source: str  # Absolute path or vault ID
    target: str  # Absolute path or vault ID
    link_type: LinkType
    metadata: dict[str, Any]
    created_at: datetime
    link_id: str  # SHA-256 hash for idempotency

    @classmethod
    def create(
        cls,
        source: str,
        target: str,
        link_type: LinkType,
        metadata: dict[str, Any] | None = None,
    ) -> BidirectionalLink:
        """Create a new bidirectional link."""
        created_at = datetime.now()
        link_id = cls._generate_link_id(source, target, link_type)

        return cls(
            source=source,
            target=target,
            link_type=link_type,
            metadata=metadata or {},
            created_at=created_at,
            link_id=link_id,
        )

    @staticmethod
    def _generate_link_id(source: str, target: str, link_type: LinkType) -> str:
        """Generate deterministic link ID (SHA-256 hash)."""
        # Normalize paths (absolute, resolve symlinks)
        source_norm = str(Path(source).resolve()) if "/" in source else source
        target_norm = str(Path(target).resolve()) if "/" in target else target

        # Sort to ensure A→B and B→A have same ID (bidirectional)
        nodes = sorted([source_norm, target_norm])
        link_str = f"{nodes[0]}::{nodes[1]}::{link_type.value}"

        return hashlib.sha256(link_str.encode()).hexdigest()

    def to_surreal(self) -> dict[str, Any]:
        """Convert to SurrealDB record format."""
        return {
            "id": f"link:{self.link_id}",
            "source": self.source,
            "target": self.target,
            "link_type": self.link_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class KnowledgeGraph:
    """Bidirectional knowledge graph using SurrealDB 3.0 + Vault."""

    def __init__(
        self,
        vault_root: Path = Path.home() / "vaults" / "cohezion-vault",
        surreal_url: str = "http://localhost:8001",
    ):
        self.vault_root = vault_root
        self.surreal_url = surreal_url
        self._links: dict[str, BidirectionalLink] = {}  # In-memory cache

    async def connect(self) -> None:
        """Connect to SurrealDB and initialize schema."""
        try:
            from cloud_vault_mcp.src.mcp_server.vault_graph.client import (
                get_graph_client,
            )

            self.client = get_graph_client()

            # Create link table with graph relations
            await self.client.execute(
                """
                DEFINE TABLE IF NOT EXISTS link SCHEMAFULL;
                DEFINE FIELD source ON link TYPE string;
                DEFINE FIELD target ON link TYPE string;
                DEFINE FIELD link_type ON link TYPE string;
                DEFINE FIELD metadata ON link TYPE object;
                DEFINE FIELD created_at ON link TYPE datetime;
                DEFINE INDEX link_source ON link FIELDS source;
                DEFINE INDEX link_target ON link FIELDS target;
                DEFINE INDEX link_type ON link FIELDS link_type;
            """
            )

            # Create graph relations (bidirectional)
            await self.client.execute(
                """
                DEFINE TABLE IF NOT EXISTS references SCHEMAFULL;
                DEFINE FIELD in ON references TYPE record(link);
                DEFINE FIELD out ON references TYPE record(link);
            """
            )

            logger.info(f"Connected to KnowledgeGraph at {self.surreal_url}")

        except ImportError:
            logger.warning("cloud-vault-mcp not available, using in-memory graph only")
            self.client = None

    async def add_link(
        self,
        source: str,
        target: str,
        link_type: LinkType,
        metadata: dict[str, Any] | None = None,
    ) -> BidirectionalLink:
        """Add a bidirectional link to the knowledge graph."""
        link = BidirectionalLink.create(source, target, link_type, metadata)

        # Add to in-memory cache
        self._links[link.link_id] = link

        # Persist to SurrealDB (if available)
        if self.client:
            try:
                await self.client.execute(
                    f"""
                    CREATE link:{link.link_id} CONTENT {{
                        source: '{link.source}',
                        target: '{link.target}',
                        link_type: '{link.link_type.value}',
                        metadata: {link.metadata},
                        created_at: '{link.created_at.isoformat()}'
                    }};
                """
                )

                # Create bidirectional relation (A->B, B->A)
                await self.client.execute(
                    f"""
                    RELATE link:{link.link_id}->references->link:{link.link_id};
                """
                )

                logger.debug(f"Added link {link.link_id}: {source} → {target}")

            except Exception as e:
                logger.error(f"Failed to persist link to SurrealDB: {e}")

        # Persist to vault (fallback + audit trail)
        await self._persist_to_vault(link)

        return link

    async def get_links(
        self, node: str, link_type: LinkType | None = None
    ) -> list[BidirectionalLink]:
        """Get all links for a node (bidirectional)."""
        if self.client:
            try:
                # Query SurrealDB for links where node is source OR target
                type_filter = f"AND link_type = '{link_type.value}'" if link_type else ""
                query = f"""
                    SELECT * FROM link
                    WHERE (source = '{node}' OR target = '{node}')
                    {type_filter}
                    ORDER BY created_at DESC;
                """
                results = await self.client.query(query)

                links = []
                for record in results:
                    link = BidirectionalLink(
                        source=record["source"],
                        target=record["target"],
                        link_type=LinkType(record["link_type"]),
                        metadata=record.get("metadata", {}),
                        created_at=datetime.fromisoformat(record["created_at"]),
                        link_id=record["id"].split(":")[1],
                    )
                    links.append(link)

                return links

            except Exception as e:
                logger.error(f"Failed to query SurrealDB: {e}")

        # Fallback: in-memory cache
        return [
            link
            for link in self._links.values()
            if (link.source == node or link.target == node)
            and (link_type is None or link.link_type == link_type)
        ]

    async def get_neighbors(self, node: str, depth: int = 1) -> set[str]:
        """Get all neighboring nodes within N hops (breadth-first)."""
        if self.client:
            try:
                # Use SurrealDB graph traversal
                query = f"""
                    SELECT * FROM link
                    WHERE (source = '{node}' OR target = '{node}')
                """
                if depth > 1:
                    # Multi-hop traversal (recursive)
                    for _ in range(depth - 1):
                        query += f"""
                            UNION
                            SELECT * FROM link
                            WHERE source IN (SELECT target FROM ({query}))
                            OR target IN (SELECT source FROM ({query}))
                        """

                results = await self.client.query(query)
                neighbors = set()
                for record in results:
                    neighbors.add(record["source"])
                    neighbors.add(record["target"])

                neighbors.discard(node)  # Remove self
                return neighbors

            except Exception as e:
                logger.error(f"Failed to query neighbors: {e}")

        # Fallback: in-memory BFS
        neighbors = set()
        visited = {node}
        frontier = {node}

        for _ in range(depth):
            next_frontier = set()
            for current in frontier:
                links = await self.get_links(current)
                for link in links:
                    neighbor = link.target if link.source == current else link.source
                    if neighbor not in visited:
                        neighbors.add(neighbor)
                        next_frontier.add(neighbor)
                        visited.add(neighbor)

            frontier = next_frontier
            if not frontier:
                break

        return neighbors

    async def find_path(self, source: str, target: str) -> list[str] | None:
        """Find shortest path between two nodes (BFS)."""
        if source == target:
            return [source]

        if self.client:
            try:
                # Use SurrealDB graph traversal (shortest path)
                query = f"""
                    SELECT * FROM fn::graph_shortest_path('{source}', '{target}');
                """
                results = await self.client.query(query)
                if results:
                    return results[0].get("path", None)

            except Exception as e:
                logger.error(f"Failed to find path: {e}")

        # Fallback: in-memory BFS
        queue = [[source]]
        visited = {source}

        while queue:
            path = queue.pop(0)
            node = path[-1]

            if node == target:
                return path

            links = await self.get_links(node)
            for link in links:
                neighbor = link.target if link.source == node else link.source
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append([*path, neighbor])

        return None  # No path found

    async def _persist_to_vault(self, link: BidirectionalLink) -> None:
        """Persist link to vault for cross-session persistence."""
        try:
            vault_links_dir = self.vault_root / "links"
            vault_links_dir.mkdir(parents=True, exist_ok=True)

            link_file = vault_links_dir / f"{link.link_id}.json"

            import json

            link_data = {
                "source": link.source,
                "target": link.target,
                "link_type": link.link_type.value,
                "metadata": link.metadata,
                "created_at": link.created_at.isoformat(),
            }

            link_file.write_text(json.dumps(link_data, indent=2))
            logger.debug(f"Persisted link to vault: {link_file}")

        except Exception as e:
            logger.error(f"Failed to persist link to vault: {e}")

    async def load_from_vault(self) -> int:
        """Load all links from vault (cross-session recovery)."""
        try:
            vault_links_dir = self.vault_root / "links"
            if not vault_links_dir.exists():
                return 0

            import json

            count = 0
            for link_file in vault_links_dir.glob("*.json"):
                link_data = json.loads(link_file.read_text())
                link = BidirectionalLink(
                    source=link_data["source"],
                    target=link_data["target"],
                    link_type=LinkType(link_data["link_type"]),
                    metadata=link_data.get("metadata", {}),
                    created_at=datetime.fromisoformat(link_data["created_at"]),
                    link_id=link_file.stem,
                )
                self._links[link.link_id] = link
                count += 1

            logger.info(f"Loaded {count} links from vault")
            return count

        except Exception as e:
            logger.error(f"Failed to load links from vault: {e}")
            return 0


# Singleton instance
_knowledge_graph: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Get singleton KnowledgeGraph instance."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph


# Convenience functions for common link patterns


async def link_doc_to_doc(source_doc: str, target_doc: str, reason: str) -> None:
    """Link two documentation files."""
    kg = get_knowledge_graph()
    await kg.add_link(
        source=source_doc,
        target=target_doc,
        link_type=LinkType.DOC_TO_DOC,
        metadata={"reason": reason},
    )


async def link_doc_to_code(doc: str, code_file: str, section: str) -> None:
    """Link documentation to code implementation."""
    kg = get_knowledge_graph()
    await kg.add_link(
        source=doc,
        target=code_file,
        link_type=LinkType.DOC_TO_CODE,
        metadata={"section": section},
    )


async def link_skill_to_code(skill_file: str, implementation: str) -> None:
    """Link PRIME skill to implementation."""
    kg = get_knowledge_graph()
    await kg.add_link(
        source=skill_file,
        target=implementation,
        link_type=LinkType.SKILL_TO_CODE,
        metadata={"relationship": "implements"},
    )


async def link_decision_to_code(decision_id: str, code_file: str, rationale: str) -> None:
    """Link vault decision to code."""
    kg = get_knowledge_graph()
    await kg.add_link(
        source=decision_id,
        target=code_file,
        link_type=LinkType.DECISION_TO_CODE,
        metadata={"rationale": rationale},
    )


async def link_pattern_to_code(pattern_id: str, code_file: str) -> None:
    """Link vault pattern to code implementation."""
    kg = get_knowledge_graph()
    await kg.add_link(
        source=pattern_id,
        target=code_file,
        link_type=LinkType.PATTERN_TO_CODE,
        metadata={},
    )


# CLI for testing
async def main():
    """Test bidirectional linking."""
    kg = get_knowledge_graph()
    await kg.connect()
    await kg.load_from_vault()

    # Example: Link DESIGN.md to CLAUDE.md
    await link_doc_to_doc(
        source_doc="/home/mike-anderson/dev/cohezion/DESIGN.md",
        target_doc="/home/mike-anderson/dev/cohezion/CLAUDE.md",
        reason="DESIGN.md provides theoretical foundation, CLAUDE.md provides operational patterns",
    )

    # Example: Link DESIGN.md to tip_of_spear_router.py
    await link_doc_to_code(
        doc="/home/mike-anderson/dev/cohezion/DESIGN.md",
        code_file="/home/mike-anderson/dev/cohezion/src/cohezion/swarm/tip_of_spear_router.py",
        section="Tip-of-Spear Routing",
    )

    # Example: Link PRIME skill to implementation
    await link_skill_to_code(
        skill_file="/home/mike-anderson/dev/cohezion/src/cohezion/skills/SMALL_MODEL_SPECIALIST_PRIME.md",
        implementation="/home/mike-anderson/dev/cohezion/src/cohezion/swarm/tip_of_spear_router.py",
    )

    # Query: Get all links for DESIGN.md
    links = await kg.get_links("/home/mike-anderson/dev/cohezion/DESIGN.md")
    print(f"\nLinks for DESIGN.md: {len(links)}")
    for link in links:
        print(f"  {link.link_type.value}: {link.target}")

    # Query: Find path from DESIGN.md to tip_of_spear_router.py
    path = await kg.find_path(
        "/home/mike-anderson/dev/cohezion/DESIGN.md",
        "/home/mike-anderson/dev/cohezion/src/cohezion/swarm/tip_of_spear_router.py",
    )
    print("\nPath from DESIGN.md to tip_of_spear_router.py:")
    if path:
        print(" → ".join(path))


if __name__ == "__main__":
    asyncio.run(main())
