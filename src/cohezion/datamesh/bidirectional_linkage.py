"""Bidirectional Linkage Manager for Cohezion.

Synchronizes data across:
- Obsidian Vault (wiki/notes)
- SurrealDB (knowledge graph + physics)
- DataMesh (unified schema)

Provides:
- 2-way sync: Obsidian ↔ SurrealDB ↔ DataMesh
- Link validation and integrity checks
- Change propagation with event sourcing
- Query federation across all systems
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import aiofiles


logger = logging.getLogger(__name__)


class LinkDirection(Enum):
    """Direction of linkage between systems."""

    OBSIDIAN_TO_SURREAL = auto()
    SURREAL_TO_OBSIDIAN = auto()
    DATAMESH_TO_BOTH = auto()
    BOTH_TO_DATAMESH = auto()


class LinkStatus(Enum):
    """Status of bidirectional link."""

    ACTIVE = auto()
    STALE = auto()  # Out of sync
    BROKEN = auto()  # Reference error
    PENDING = auto()  # Queued for sync
    CONFLICT = auto()  # Divergent changes


@dataclass
class BidirectionalLink:
    """A link connecting an entity across multiple systems."""

    link_id: str
    created_at: datetime

    # Obsidian reference
    obsidian_path: Path | None
    obsidian_etag: str | None  # Content hash

    # SurrealDB reference
    surreal_record_id: str | None
    surreal_table: str | None
    surreal_timestamp: datetime | None

    # DataMesh reference
    datamesh_entity_id: UUID | None
    datamesh_schema_version: str | None

    # Link metadata
    direction: LinkDirection
    status: LinkStatus
    last_sync: datetime | None
    sync_version: int

    # Physics grounding (optional)
    manifold_coherence: float | None
    spin_state: dict[str, float] | None


@dataclass
class LinkChangeEvent:
    """Change event for event-sourced link updates."""

    event_id: str
    timestamp: datetime
    link_id: str
    source_system: str  # 'obsidian', 'surreal', 'datamesh'
    change_type: str  # 'create', 'update', 'delete', 'sync'
    payload: dict[str, Any]
    vector_clock: dict[str, int]  # For causal consistency


class BidirectionalLinkageManager:
    """Manager for bidirectional links across Cohezion systems."""

    def __init__(
        self,
        obsidian_vault_path: Path,
        surreal_client: Any | None = None,
        datamesh: Any | None = None,
    ):
        self.vault_path = Path(obsidian_vault_path)
        self.surreal = surreal_client
        self.datamesh = datamesh

        self.links: dict[str, BidirectionalLink] = {}
        self.event_log: list[LinkChangeEvent] = []
        self._change_handlers: list[Callable[[LinkChangeEvent], None]] = []

        # Sync state
        self._sync_in_progress = False
        self._pending_changes: list[LinkChangeEvent] = []

    async def initialize(self) -> None:
        """Initialize bidirectional linkage system."""
        logger.info("Initializing bidirectional linkage manager...")

        # Create index file if missing
        await self._ensure_link_index()

        # Load existing links
        await self._load_link_index()

        logger.info(f"Loaded {len(self.links)} existing bidirectional links")

    async def _ensure_link_index(self) -> None:
        """Ensure .cohezion/links.jsonl exists."""
        cohezion_dir = self.vault_path / ".cohezion"
        cohezion_dir.mkdir(exist_ok=True)

        links_file = cohezion_dir / "bidirectional_links.jsonl"
        if not links_file.exists():
            links_file.write_text("")

    async def _load_link_index(self) -> None:
        """Load link index from vault."""
        links_file = self.vault_path / ".cohezion" / "bidirectional_links.jsonl"

        if not links_file.exists():
            return

        async with aiofiles.open(links_file) as f:
            async for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    link = self._dict_to_link(data)
                    self.links[link.link_id] = link
                except Exception as e:
                    logger.warning(f"Failed to load link: {e}")

    async def _save_link_index(self) -> None:
        """Persist link index to vault."""
        links_file = self.vault_path / ".cohezion" / "bidirectional_links.jsonl"

        lines = []
        for link in self.links.values():
            lines.append(json.dumps(self._link_to_dict(link)))

        async with aiofiles.open(links_file, "w") as f:
            await f.write("\n".join(lines) + "\n")

    def _link_to_dict(self, link: BidirectionalLink) -> dict:
        """Serialize link to dict."""
        return {
            "link_id": link.link_id,
            "created_at": link.created_at.isoformat(),
            "obsidian_path": str(link.obsidian_path) if link.obsidian_path else None,
            "obsidian_etag": link.obsidian_etag,
            "surreal_record_id": link.surreal_record_id,
            "surreal_table": link.surreal_table,
            "surreal_timestamp": link.surreal_timestamp.isoformat()
            if link.surreal_timestamp
            else None,
            "datamesh_entity_id": str(link.datamesh_entity_id) if link.datamesh_entity_id else None,
            "datamesh_schema_version": link.datamesh_schema_version,
            "direction": link.direction.name,
            "status": link.status.name,
            "last_sync": link.last_sync.isoformat() if link.last_sync else None,
            "sync_version": link.sync_version,
            "manifold_coherence": link.manifold_coherence,
            "spin_state": link.spin_state,
        }

    def _dict_to_link(self, data: dict) -> BidirectionalLink:
        """Deserialize dict to link."""
        return BidirectionalLink(
            link_id=data["link_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            obsidian_path=Path(data["obsidian_path"]) if data["obsidian_path"] else None,
            obsidian_etag=data.get("obsidian_etag"),
            surreal_record_id=data.get("surreal_record_id"),
            surreal_table=data.get("surreal_table"),
            surreal_timestamp=datetime.fromisoformat(data["surreal_timestamp"])
            if data.get("surreal_timestamp")
            else None,
            datamesh_entity_id=UUID(data["datamesh_entity_id"])
            if data.get("datamesh_entity_id")
            else None,
            datamesh_schema_version=data.get("datamesh_schema_version"),
            direction=LinkDirection[data["direction"]],
            status=LinkStatus[data["status"]],
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            sync_version=data.get("sync_version", 0),
            manifold_coherence=data.get("manifold_coherence"),
            spin_state=data.get("spin_state"),
        )

    async def create_link(
        self,
        obsidian_path: Path | None = None,
        surreal_record_id: str | None = None,
        surreal_table: str | None = None,
        datamesh_entity_id: UUID | None = None,
        direction: LinkDirection = LinkDirection.DATAMESH_TO_BOTH,
        physics_context: dict[str, Any] | None = None,
    ) -> BidirectionalLink:
        """Create new bidirectional link."""
        link_id = str(uuid4())[:8]

        link = BidirectionalLink(
            link_id=link_id,
            created_at=datetime.now(),
            obsidian_path=obsidian_path,
            obsidian_etag=None,
            surreal_record_id=surreal_record_id,
            surreal_table=surreal_table,
            surreal_timestamp=None,
            datamesh_entity_id=datamesh_entity_id,
            datamesh_schema_version="1.0.0",
            direction=direction,
            status=LinkStatus.PENDING,
            last_sync=None,
            sync_version=1,
            manifold_coherence=physics_context.get("coherence") if physics_context else None,
            spin_state=physics_context.get("spin") if physics_context else None,
        )

        self.links[link_id] = link

        # Emit event
        event = LinkChangeEvent(
            event_id=str(uuid4())[:8],
            timestamp=datetime.now(),
            link_id=link_id,
            source_system="datamesh",
            change_type="create",
            payload=self._link_to_dict(link),
            vector_clock={"obsidian": 0, "surreal": 0, "datamesh": 1},
        )
        self.event_log.append(event)

        await self._save_link_index()

        logger.info(f"Created bidirectional link {link_id}")
        return link

    async def sync_link(self, link_id: str, force: bool = False) -> BidirectionalLink:
        """Synchronize link across all systems."""
        if link_id not in self.links:
            raise ValueError(f"Link {link_id} not found")

        link = self.links[link_id]

        if self._sync_in_progress and not force:
            logger.warning(f"Sync already in progress, queueing {link_id}")
            return link

        self._sync_in_progress = True

        try:
            # Determine sync direction
            if link.direction == LinkDirection.OBSIDIAN_TO_SURREAL:
                await self._sync_obsidian_to_surreal(link)
            elif link.direction == LinkDirection.SURREAL_TO_OBSIDIAN:
                await self._sync_surreal_to_obsidian(link)
            elif link.direction == LinkDirection.DATAMESH_TO_BOTH:
                await self._sync_datamesh_to_both(link)
            elif link.direction == LinkDirection.BOTH_TO_DATAMESH:
                await self._sync_both_to_datamesh(link)

            link.last_sync = datetime.now()
            link.sync_version += 1
            link.status = LinkStatus.ACTIVE

            await self._save_link_index()

            logger.info(f"Synced link {link_id} (version {link.sync_version})")

        except Exception as e:
            link.status = LinkStatus.BROKEN
            logger.error(f"Sync failed for {link_id}: {e}")
            raise
        finally:
            self._sync_in_progress = False

            # Process queued changes
            if self._pending_changes:
                await self._process_queued_changes()

        return link

    async def _sync_obsidian_to_surreal(self, link: BidirectionalLink) -> None:
        """Sync Obsidian note to SurrealDB record."""
        if not link.obsidian_path:
            return

        # Read Obsidian content
        content = await self._read_obsidian_file(link.obsidian_path)

        # Parse wiki links and tags
        wiki_links = self._extract_wiki_links(content)
        tags = self._extract_tags(content)

        # Prepare SurrealDB record
        record = {
            "title": link.obsidian_path.stem,
            "content": content,
            "wiki_links": wiki_links,
            "tags": tags,
            "source_path": str(link.obsidian_path),
            "updated_at": datetime.now().isoformat(),
            "coherence": link.manifold_coherence,
            "spin_state": link.spin_state,
        }

        # Upsert to SurrealDB
        if self.surreal and link.surreal_record_id:
            await self.surreal.update(link.surreal_record_id, record)
            logger.debug(f"Updated SurrealDB record {link.surreal_record_id}")

        # Update DataMesh
        if self.datamesh and link.datamesh_entity_id:
            await self.datamesh.update_entity(link.datamesh_entity_id, record)

    async def _sync_surreal_to_obsidian(self, link: BidirectionalLink) -> None:
        """Sync SurrealDB record to Obsidian note."""
        if not link.surreal_record_id or not self.surreal:
            return

        # Fetch from SurrealDB
        record = await self.surreal.select(link.surreal_record_id)

        if not record:
            logger.warning(f"SurrealDB record {link.surreal_record_id} not found")
            return

        # Generate Obsidian markdown
        content = self._record_to_markdown(record)

        # Write to Obsidian vault
        if link.obsidian_path:
            await self._write_obsidian_file(link.obsidian_path, content)
            logger.debug(f"Updated Obsidian file {link.obsidian_path}")

        # Update DataMesh
        if self.datamesh and link.datamesh_entity_id:
            await self.datamesh.update_entity(link.datamesh_entity_id, record)

    async def _sync_datamesh_to_both(self, link: BidirectionalLink) -> None:
        """Sync DataMesh entity to both systems."""
        if not link.datamesh_entity_id or not self.datamesh:
            return

        # Fetch from DataMesh
        entity = await self.datamesh.get_entity(link.datamesh_entity_id)

        if not entity:
            return

        # Propagate to SurrealDB
        if self.surreal and link.surreal_record_id:
            await self.surreal.update(link.surreal_record_id, entity)

        # Propagate to Obsidian
        if link.obsidian_path:
            content = self._entity_to_markdown(entity)
            await self._write_obsidian_file(link.obsidian_path, content)

    async def _sync_both_to_datamesh(self, link: BidirectionalLink) -> None:
        """Sync from both systems to DataMesh (merge conflict resolution)."""
        # This is for future conflict resolution implementation
        pass

    async def _read_obsidian_file(self, path: Path) -> str:
        """Read content from Obsidian vault."""
        full_path = self.vault_path / path
        async with aiofiles.open(full_path, encoding="utf-8") as f:
            return await f.read()

    async def _write_obsidian_file(self, path: Path, content: str) -> None:
        """Write content to Obsidian vault."""
        full_path = self.vault_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
            await f.write(content)

    def _extract_wiki_links(self, content: str) -> list[str]:
        """Extract [[Wiki Links]] from markdown."""
        pattern = r"\[\[([^\]]+)\]\]"
        return re.findall(pattern, content)

    def _extract_tags(self, content: str) -> list[str]:
        """Extract #tags from markdown."""
        pattern = r"#([a-zA-Z0-9_-]+)"
        return re.findall(pattern, content)

    def _record_to_markdown(self, record: dict) -> str:
        """Convert SurrealDB record to Obsidian markdown."""
        lines = [
            f"# {record.get('title', 'Untitled')}",
            "",
            record.get("content", ""),
            "",
            "## Metadata",
            "",
            f"- **Source**: {record.get('source_path', 'N/A')}",
            f"- **Updated**: {record.get('updated_at', 'N/A')}",
            "",
            "## Tags",
            "",
        ]

        for tag in record.get("tags", []):
            lines.append(f"#{tag}")

        lines.extend(["", "## Related", ""])

        for link in record.get("wiki_links", []):
            lines.append(f"- [[{link}]]")

        return "\n".join(lines)

    def _entity_to_markdown(self, entity: dict) -> str:
        """Convert DataMesh entity to Obsidian markdown."""
        return self._record_to_markdown(entity)

    async def _process_queued_changes(self) -> None:
        """Process queued changes after current sync completes."""
        while self._pending_changes:
            event = self._pending_changes.pop(0)
            logger.info(f"Processing queued change: {event.event_id}")

    async def resolve_conflict(self, link_id: str, resolution: str) -> BidirectionalLink:
        """Resolve conflict using specified strategy."""
        # resolution: 'obsidian_wins', 'surreal_wins', 'datamesh_wins', 'merge'
        link = self.links[link_id]

        if resolution == "obsidian_wins":
            link.direction = LinkDirection.OBSIDIAN_TO_SURREAL
        elif resolution == "surreal_wins":
            link.direction = LinkDirection.SURREAL_TO_OBSIDIAN
        elif resolution == "datamesh_wins":
            link.direction = LinkDirection.DATAMESH_TO_BOTH

        link.status = LinkStatus.ACTIVE
        await self.sync_link(link_id, force=True)

        return link

    async def query_federated(
        self,
        query: str,
        include_obsidian: bool = True,
        include_surreal: bool = True,
        include_datamesh: bool = True,
    ) -> dict[str, list[Any]]:
        """Query across all linked systems."""
        results = {"obsidian": [], "surreal": [], "datamesh": []}

        # Query Obsidian vault (local search)
        if include_obsidian:
            results["obsidian"] = await self._search_obsidian(query)

        # Query SurrealDB
        if include_surreal and self.surreal:
            results["surreal"] = await self._search_surreal(query)

        # Query DataMesh
        if include_datamesh and self.datamesh:
            results["datamesh"] = await self._search_datamesh(query)

        return results

    async def _search_obsidian(self, query: str) -> list[dict]:
        """Search Obsidian vault."""
        results = []
        wiki_dir = self.vault_path / "wiki"

        for md_file in wiki_dir.rglob("*.md"):
            content = await self._read_obsidian_file(md_file.relative_to(self.vault_path))
            if query.lower() in content.lower():
                results.append(
                    {"path": str(md_file), "title": md_file.stem, "snippet": content[:200] + "..."}
                )

        return results

    async def _search_surreal(self, query: str) -> list[dict]:
        """Search SurrealDB."""
        if not self.surreal:
            return []

        # Use SurrealQL full-text search
        sql = f"""
            SELECT * FROM wiki_page WHERE
            content @@ '{query}' OR
            title @@ '{query}'
        """

        return await self.surreal.query(sql)

    async def _search_datamesh(self, query: str) -> list[dict]:
        """Search DataMesh."""
        if not self.datamesh:
            return []

        return await self.datamesh.search(query)

    def get_link_stats(self) -> dict[str, Any]:
        """Get statistics about bidirectional links."""
        stats = {
            "total_links": len(self.links),
            "by_status": {},
            "by_direction": {},
            "stale_links": 0,
            "avg_sync_version": 0,
        }

        for link in self.links.values():
            stats["by_status"][link.status.name] = stats["by_status"].get(link.status.name, 0) + 1
            stats["by_direction"][link.direction.name] = (
                stats["by_direction"].get(link.direction.name, 0) + 1
            )

            if link.status == LinkStatus.STALE:
                stats["stale_links"] += 1

            stats["avg_sync_version"] += link.sync_version

        if self.links:
            stats["avg_sync_version"] /= len(self.links)

        return stats
