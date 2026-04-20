"""Real-time configuration monitoring.

Integrates VaultSubscriptionClient and VaultFileWatcher to detect
changes and emit ConfigEvents for vault and config file modifications.

Phase 2: Real-time event-driven monitoring.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime
from pathlib import Path

from cohezion.config.config_events import ConfigEvent
from cohezion.config.config_state import FileMetadata
from cohezion.config.git_utils import GitUtils
from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.core.vault_subscription import VaultEvent, VaultSubscriptionClient


logger = logging.getLogger(__name__)


class ConfigMonitor:
    """Real-time monitoring for configuration changes.

    Monitors:
    1. Vault via VaultSubscriptionClient (SSE)
    2. Config files via periodic polling
    3. Manual edits via git history

    Emits ConfigEvent via EventBus.
    """

    def __init__(
        self,
        repo_root: Path | None = None,
        vault_url: str = "http://localhost:8360",
        vault_api_key: str = "",
    ):
        """Initialize config monitor."""
        if repo_root is None:
            repo_root = Path.cwd()
        self.repo_root = Path(repo_root)
        self.vault_url = vault_url
        self.vault_api_key = vault_api_key
        self.git_utils = GitUtils(repo_root)
        self.event_bus = EventBus()

        # File tracking
        self.claude_md = repo_root / "CLAUDE.md"
        self.gemini_md = repo_root / "GEMINI.md"
        self.last_claude_hash: str | None = None
        self.last_gemini_hash: str | None = None

        # Vault subscription
        self.vault_client = VaultSubscriptionClient(vault_url, vault_api_key)
        self._running = False

    async def start(self) -> None:
        """Start all monitoring tasks."""
        if self._running:
            logger.warning("Monitor already running")
            return

        self._running = True
        logger.info("Starting config monitoring")

        try:
            # Register vault event handlers
            self._register_vault_handlers()

            # Run monitoring tasks concurrently
            await asyncio.gather(
                self.vault_client.connect(),
                self._monitor_config_files(),
            )

        except asyncio.CancelledError:
            logger.info("Monitoring cancelled")
        except Exception as e:
            logger.error(f"Monitoring error: {e}", exc_info=True)
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop monitoring tasks."""
        self._running = False
        await self.vault_client.disconnect()
        logger.info("Config monitoring stopped")

    def _register_vault_handlers(self) -> None:
        """Register handlers for vault SSE events."""

        @self.vault_client.on_event("file_created")
        async def on_vault_file_created(event: VaultEvent) -> None:
            """Handle vault file creation."""
            await self._handle_vault_create(event)

        @self.vault_client.on_event("file_modified")
        async def on_vault_file_modified(event: VaultEvent) -> None:
            """Handle vault file modification."""
            await self._handle_vault_modify(event)

        @self.vault_client.on_event("file_deleted")
        async def on_vault_file_deleted(event: VaultEvent) -> None:
            """Handle vault file deletion."""
            await self._handle_vault_delete(event)

    async def _handle_vault_create(self, event: VaultEvent) -> None:
        """Process vault file creation."""
        logger.info(f"Vault file created: {event.path}")

        # Classify the event
        if event.path.startswith("decisions/"):
            config_event = Event(
                type=EventType.CUSTOM,
                source="config-monitor",
                payload={
                    "config_event": ConfigEvent.VAULT_DECISION_ADDED.name,
                    "path": event.path,
                    "timestamp": event.timestamp,
                },
            )
            self.event_bus.publish(config_event)

        elif event.path.startswith("patterns/"):
            config_event = Event(
                type=EventType.CUSTOM,
                source="config-monitor",
                payload={
                    "config_event": ConfigEvent.VAULT_PATTERN_UPDATED.name,
                    "path": event.path,
                    "timestamp": event.timestamp,
                },
            )
            self.event_bus.publish(config_event)

        elif event.path.startswith("experiments/"):
            config_event = Event(
                type=EventType.CUSTOM,
                source="config-monitor",
                payload={
                    "config_event": ConfigEvent.VAULT_EXPERIMENT_CREATED.name,
                    "path": event.path,
                    "timestamp": event.timestamp,
                },
            )
            self.event_bus.publish(config_event)

    async def _handle_vault_modify(self, event: VaultEvent) -> None:
        """Process vault file modification."""
        logger.info(f"Vault file modified: {event.path}")

        if event.path.startswith("patterns/"):
            config_event = Event(
                type=EventType.CUSTOM,
                source="config-monitor",
                payload={
                    "config_event": ConfigEvent.VAULT_PATTERN_UPDATED.name,
                    "path": event.path,
                    "timestamp": event.timestamp,
                },
            )
            self.event_bus.publish(config_event)

    async def _handle_vault_delete(self, event: VaultEvent) -> None:
        """Process vault file deletion."""
        logger.info(f"Vault file deleted: {event.path}")

    async def _monitor_config_files(self) -> None:
        """Monitor CLAUDE.md and GEMINI.md for changes.

        Phase 2: Simple polling approach.
        Phase 3: Can integrate with VaultFileWatcher for native filesystem events.
        """
        while self._running:
            try:
                await self._check_config_file(self.claude_md, "CLAUDE.md")
                await self._check_config_file(self.gemini_md, "GEMINI.md")

                # Check every 30 seconds
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Config file monitoring error: {e}")
                await asyncio.sleep(30)

    async def _check_config_file(self, file_path: Path, filename: str) -> None:
        """Check if a config file has changed."""
        if not file_path.exists():
            return

        try:
            metadata = FileMetadata.from_file(file_path)
            current_hash = metadata.content_hash

            # Get previous hash
            if filename == "CLAUDE.md":
                previous_hash = self.last_claude_hash
                self.last_claude_hash = current_hash
            else:
                previous_hash = self.last_gemini_hash
                self.last_gemini_hash = current_hash

            # Detect change
            if previous_hash and previous_hash != current_hash:
                await self._handle_config_file_change(file_path, filename)

        except Exception as e:
            logger.warning(f"Error checking {filename}: {e}")

    async def _handle_config_file_change(self, file_path: Path, filename: str) -> None:
        """Handle configuration file change."""
        logger.info(f"Config file changed: {filename}")

        # Detect if manually edited or auto-generated
        is_manual = self.git_utils.is_manual_edit(file_path)

        if is_manual:
            logger.info(f"Manual edit detected in {filename}")

            # Get diff to understand what changed
            diff = self.git_utils.get_file_diff(file_path)

            config_event = Event(
                type=EventType.CUSTOM,
                source="config-monitor",
                payload={
                    "config_event": ConfigEvent.MANUAL_EDIT_DETECTED.name,
                    "file": filename,
                    "timestamp": datetime.now().isoformat(),
                    "has_diff": diff is not None,
                },
            )
            self.event_bus.publish(config_event)
        else:
            logger.debug(f"Auto-generated change in {filename}")

            config_event = Event(
                type=EventType.CUSTOM,
                source="config-monitor",
                payload={
                    "config_event": ConfigEvent.CONFIG_FILE_MODIFIED.name,
                    "file": filename,
                    "timestamp": datetime.now().isoformat(),
                    "auto_generated": True,
                },
            )
            self.event_bus.publish(config_event)


class VaultSubscriptionClientProxy:
    """Proxy to manage VaultSubscriptionClient lifecycle."""

    def __init__(self, base_url: str = "http://localhost:8360", api_key: str = ""):
        """Initialize proxy."""
        self.base_url = base_url
        self.api_key = api_key
        self.client = VaultSubscriptionClient(base_url, api_key)
        self._task: asyncio.Task | None = None

    async def start_background(self) -> None:
        """Start subscription in background task."""
        if self._task and not self._task.done():
            logger.warning("Subscription already running")
            return

        self._task = asyncio.create_task(self.client.connect())
        logger.info("Vault subscription started in background")

    async def stop(self) -> None:
        """Stop subscription."""
        await self.client.disconnect()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Vault subscription stopped")

    def on_event(self, event_type: str):
        """Register event handler (proxy to client)."""
        return self.client.on_event(event_type)

    def on_all(self):
        """Register global handler (proxy to client)."""
        return self.client.on_all()
