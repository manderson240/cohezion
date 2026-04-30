"""Event wiring for configuration orchestration.

Subscribes to vault/config changes and triggers sync operations.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


class CommitBatcher:
    """Batches commit operations to prevent git churn.

    Accumulates changes for a configurable window before committing.
    Prevents 50-100 commits/day from rapid vault changes.
    """

    def __init__(self, batch_window_seconds: int = 300):
        """Initialize batcher.

        Args:
            batch_window_seconds: Accumulate changes for this many seconds (default: 5min)
        """
        self.batch_window_seconds = batch_window_seconds
        self.pending_files: set[str] = set()
        self.last_commit: datetime | None = None
        self._lock = asyncio.Lock()

    async def queue_file(self, filename: str) -> None:
        """Queue a file for batched commit."""
        async with self._lock:
            self.pending_files.add(filename)
            logger.debug(f"Queued {filename} for batch commit. Pending: {len(self.pending_files)}")

    async def should_commit(self) -> bool:
        """Check if batch window exceeded and commit should happen."""
        async with self._lock:
            if not self.pending_files:
                return False

            if self.last_commit is None:
                # First commit, do it immediately
                return True

            elapsed = (datetime.now() - self.last_commit).total_seconds()
            return elapsed >= self.batch_window_seconds

    async def get_pending_and_reset(self) -> set[str]:
        """Get pending files and reset batch."""
        async with self._lock:
            pending = self.pending_files.copy()
            self.pending_files.clear()
            self.last_commit = datetime.now()
            return pending

    async def pending_count(self) -> int:
        """Get current number of pending files."""
        async with self._lock:
            return len(self.pending_files)

    async def reset(self) -> None:
        """Reset batcher state (for testing)."""
        async with self._lock:
            self.pending_files.clear()
            self.last_commit = None


class EventSubscriber:
    """Base class for event subscribers."""

    async def on_vault_decision_added(self, decision_name: str) -> None:
        """Handle new decision in vault."""
        pass

    async def on_vault_pattern_updated(self, pattern_name: str) -> None:
        """Handle updated pattern in vault."""
        pass

    async def on_config_file_modified(self, filename: str) -> None:
        """Handle manual config file edit."""
        pass

    async def on_sync_completed(self, filename: str) -> None:
        """Handle sync completion."""
        pass


class SyncEventSubscriber(EventSubscriber):
    """Subscriber that triggers syncs on vault changes."""

    def __init__(
        self,
        sync_callback: Callable[[str], None],
        batcher: CommitBatcher,
    ):
        """Initialize subscriber.

        Args:
            sync_callback: Function to call for sync (e.g., sync_config_file)
            batcher: CommitBatcher for batching commits
        """
        self.sync_callback = sync_callback
        self.batcher = batcher

    async def on_vault_decision_added(self, decision_name: str) -> None:
        """Trigger CLAUDE.md sync on new decision."""
        logger.info(f"Vault decision added: {decision_name}")
        await self.batcher.queue_file("CLAUDE.md")

    async def on_vault_pattern_updated(self, pattern_name: str) -> None:
        """Trigger CLAUDE.md sync on pattern update."""
        logger.info(f"Vault pattern updated: {pattern_name}")
        await self.batcher.queue_file("CLAUDE.md")

    async def on_config_file_modified(self, filename: str) -> None:
        """Log manual edits (don't auto-sync)."""
        logger.warning(f"Manual edit detected in {filename} - requires review")

    async def on_sync_completed(self, filename: str) -> None:
        """Log sync completion."""
        logger.info(f"Sync completed: {filename}")
