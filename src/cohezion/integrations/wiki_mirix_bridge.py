"""Bridge between Karpathy LLM-Wiki and MIRIX memory system."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cohezion.core.persistence.surreal_client import PhysicsState, SurrealClient, UniverseNode


try:
    from mirix import MirixClient
except ImportError:
    MirixClient = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


@dataclass
class MemoryMapping:
    """Map wiki pages to MIRIX memory types."""

    wiki_path: str
    mirix_type: str  # core, episodic, semantic, procedural, resource, knowledge
    confidence: float
    extracted_entities: list[str]


class WikiMirixBridge:
    """
    Bridge Karpathy LLM-Wiki to MIRIX multi-agent memory.

    Mapping:
    - /wiki/entities/person/*.md → Core Memory (human profile)
    - /wiki/sources/*.md → Episodic Memory (reading events)
    - /wiki/concepts/*.md → Semantic Memory (concept graph)
    - /wiki/synthesis/*.md → Knowledge Vault (compiled knowledge)
    """

    def __init__(
        self,
        wiki,
        surreal: SurrealClient | None = None,
        mirix: Any | None = None,
    ):
        from cohezion.integrations.obsidian_wiki import ObsidianWiki

        self.wiki: ObsidianWiki = wiki
        self.surreal = surreal or SurrealClient()
        self.mirix = mirix
        self._surreal_connected = False

    async def _ensure_surreal(self) -> None:
        """Lazy connect to SurrealDB."""
        if not self._surreal_connected:
            await self.surreal.connect()
            self._surreal_connected = True

    async def sync_wiki_to_mirix(self, page_path: Path | None = None) -> list[MemoryMapping]:
        """
        Sync wiki page(s) to appropriate MIRIX memory type.

        If page_path is None, sync all wiki pages.
        """
        mappings = []

        if page_path:
            pages = [self.wiki._parse_page(page_path)]
        else:
            pages = []
            for category_dir in self.wiki.wiki_dir.iterdir():
                if category_dir.is_dir():
                    for md_file in category_dir.rglob("*.md"):
                        pages.append(self.wiki._parse_page(md_file))

        for page in pages:
            mapping = self._map_to_mirix(page)
            mappings.append(mapping)

            # Sync to MIRIX if available
            if self.mirix and MirixClient:
                await self._sync_to_mirix_agent(page, mapping)

            # Sync to SurrealDB
            await self._sync_to_surreal(page, mapping)

        logger.info(f"Synced {len(mappings)} pages to MIRIX/SurrealDB")
        return mappings

    def _map_to_mirix(self, page) -> MemoryMapping:
        """Determine MIRIX memory type for a wiki page."""
        path_str = str(page.path)

        if "/entities/people/" in path_str or "/entities/organizations/" in path_str:
            mirix_type = "core"
        elif "/sources/" in path_str:
            mirix_type = "episodic"
        elif "/concepts/" in path_str:
            mirix_type = "semantic"
        elif "/synthesis/" in path_str:
            mirix_type = "knowledge"
        else:
            mirix_type = "resource"

        # Extract entities from content
        entities = []
        for link in page.backlinks:
            entities.append(link)

        return MemoryMapping(
            wiki_path=path_str,
            mirix_type=mirix_type,
            confidence=0.85,
            extracted_entities=entities,
        )

    async def _sync_to_mirix_agent(self, page, mapping: MemoryMapping) -> None:
        """Send wiki content to appropriate MIRIX memory agent."""
        if not self.mirix:
            return

        content = f"# {page.title}\n\n{page.content}"

        if mapping.mirix_type == "episodic":
            # Add to episodic memory (conversations/events)
            self.mirix.add(
                user_id="cohezion-user",
                messages=[
                    {"role": "user", "content": [{"type": "text", "text": content}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "Noted."}]},
                ],
            )
        elif mapping.mirix_type == "knowledge":
            # Add to knowledge vault
            self.mirix.add(
                user_id="cohezion-user",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Store in knowledge vault: {content}"}
                        ],
                    },
                ],
            )

        logger.debug(f"Synced to MIRIX {mapping.mirix_type}: {page.title}")

    async def _sync_to_surreal(self, page, mapping: MemoryMapping) -> None:
        """Store wiki page as SurrealDB UniverseNode."""
        await self._ensure_surreal()

        physics = PhysicsState(
            physics=mapping.confidence,  # Use physics field for coherence/salience
            time=page.updated_at.timestamp(),
        )

        node = UniverseNode(
            id=f"wiki_{hash(page.title) & 0xFFFFFFFF}",
            content=page.content[:1000],  # Truncate for DB storage
            physics_state=physics,
            metadata={
                "type": "wiki_page",
                "category": page.category,
                "title": page.title,
                "path": str(page.path),
                "mirix_type": mapping.mirix_type,
                "backlinks": page.backlinks,
                "tags": page.tags,
            },
        )

        await self.surreal.store_node(node)

        # Create relations to linked pages
        for link in page.backlinks:
            # Create relation: this_page --relates_to--> linked_page
            try:
                await self.surreal.query(
                    f"RELATE universe_nodes:wiki_{hash(page.title) & 0xFFFFFFFF}->relates_to->universe_nodes:wiki_{hash(link) & 0xFFFFFFFF}"
                )
            except Exception:
                pass  # Target may not exist yet

        logger.debug(f"Synced to SurrealDB: {page.title}")

    async def query_cross_system(
        self,
        query: str,
        use_mirix: bool = True,
        use_surreal: bool = True,
    ) -> dict[str, Any]:
        """
        Query both wiki and MIRIX for comprehensive results.

        Returns unified view with provenance.
        """
        results = {
            "query": query,
            "wiki_results": [],
            "mirix_results": [],
            "surreal_results": [],
        }

        # Query wiki (local files)
        wiki_pages = await self.wiki.query_pages(query, limit=5)
        results["wiki_results"] = [
            {"title": p.title, "category": p.category, "path": str(p.path)} for p in wiki_pages
        ]

        # Query MIRIX (if available)
        if use_mirix and self.mirix and MirixClient:
            mirix_memories = self.mirix.retrieve_with_conversation(
                user_id="cohezion-user",
                messages=[{"role": "user", "content": [{"type": "text", "text": query}]}],
                limit=5,
            )
            results["mirix_results"] = mirix_memories

        # Query SurrealDB (graph traversal)
        if use_surreal:
            await self._ensure_surreal()
            surreal_results = await self.surreal.query(
                """
                SELECT * FROM wiki
                WHERE content CONTAINS $query
                LIMIT 5
                """,
                {"query": query},
            )
            results["surreal_results"] = surreal_results[0]["result"] if surreal_results else []

        return results

    async def sync_all_to_surreal(self) -> int:
        """Sync all wiki pages to SurrealDB."""
        await self._ensure_surreal()

        count = 0
        for category_dir in self.wiki.wiki_dir.iterdir():
            if category_dir.is_dir():
                for md_file in category_dir.rglob("*.md"):
                    page = self.wiki._parse_page(md_file)
                    mapping = self._map_to_mirix(page)
                    await self._sync_to_surreal(page, mapping)
                    count += 1

        logger.info(f"Synced {count} pages to SurrealDB")
        return count
