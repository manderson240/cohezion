"""
GraphRAG Auto-Sync: Watch vault changes and sync to SurrealDB

Subscribes to VaultFileWatcher and automatically imports/updates
documents in SurrealDB when files change.
"""

import asyncio
import logging
from pathlib import Path

from .graphrag_import import GraphRAGImporter
from .vault_watcher import VaultEvent, VaultFileWatcher


logger = logging.getLogger(__name__)


class GraphRAGAutoSync:
    """Auto-sync vault changes to SurrealDB GraphRAG"""

    def __init__(
        self, vault_path: Path, watcher: VaultFileWatcher, enable_edges: bool = True
    ):
        self.vault_path = Path(vault_path).resolve()
        self.watcher = watcher
        self.enable_edges = enable_edges

        self.importer: GraphRAGImporter | None = None
        self.task: asyncio.Task | None = None
        self.queue: asyncio.Queue[VaultEvent] | None = None

    async def start(self):
        """Start auto-sync background task"""
        if self.task and not self.task.done():
            logger.warning("Auto-sync already running")
            return

        # Initialize importer
        self.importer = GraphRAGImporter(self.vault_path)
        await self.importer.__aenter__()

        # Subscribe to watcher
        self.queue = self.watcher.subscribe(maxsize=1000)

        # Start background sync task
        self.task = asyncio.create_task(self._sync_loop())
        logger.info("GraphRAG auto-sync started")

    async def stop(self):
        """Stop auto-sync background task"""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        if self.queue:
            self.watcher.unsubscribe(self.queue)
            self.queue = None

        if self.importer:
            await self.importer.__aexit__(None, None, None)
            self.importer = None

        logger.info("GraphRAG auto-sync stopped")

    async def _sync_loop(self):
        """Background task: process vault events and sync to SurrealDB"""
        if not self.queue or not self.importer:
            return

        logger.info("Auto-sync loop started")

        try:
            while True:
                # Wait for vault event
                event = await self.queue.get()

                # Only process created/modified events for .md files
                if event.event_type in ("created", "modified"):
                    file_path = self.vault_path / event.path

                    if file_path.exists() and file_path.suffix == ".md":
                        await self._sync_document(file_path)

                # For deleted events, could remove from SurrealDB
                # (not implemented yet - keep deleted docs for now)

        except asyncio.CancelledError:
            logger.info("Auto-sync loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Auto-sync loop error: {e}", exc_info=True)

    async def _sync_document(self, file_path: Path):
        """Sync single document to SurrealDB"""
        try:
            doc_id = await self.importer.import_document(
                file_path, create_edges=self.enable_edges
            )

            if doc_id:
                logger.info(f"Auto-synced {file_path.name} → {doc_id}")
            else:
                logger.warning(f"Failed to sync {file_path.name}")

        except Exception as e:
            logger.error(f"Error syncing {file_path}: {e}")


# Global auto-sync instance (singleton)
_auto_sync: GraphRAGAutoSync | None = None


async def start_autosync(
    vault_path: Path, watcher: VaultFileWatcher, enable_edges: bool = True
):
    """Start global auto-sync instance"""
    global _auto_sync

    if _auto_sync:
        logger.warning("Auto-sync already running")
        return _auto_sync

    _auto_sync = GraphRAGAutoSync(vault_path, watcher, enable_edges)
    await _auto_sync.start()
    return _auto_sync


async def stop_autosync():
    """Stop global auto-sync instance"""
    global _auto_sync

    if _auto_sync:
        await _auto_sync.stop()
        _auto_sync = None


def get_autosync() -> GraphRAGAutoSync | None:
    """Get current auto-sync instance"""
    return _auto_sync
