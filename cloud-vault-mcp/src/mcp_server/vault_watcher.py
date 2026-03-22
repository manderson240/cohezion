"""Filesystem watcher for vault changes with debounce and fan-out."""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


logger = logging.getLogger(__name__)


@dataclass
class VaultEvent:
    """A vault filesystem change event."""

    event_type: str  # "created" | "modified" | "deleted" | "moved"
    path: str  # vault-relative path
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    old_path: str | None = None  # for moves

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "path": self.path,
            "timestamp": self.timestamp.isoformat(),
            "old_path": self.old_path,
        }


class VaultFileWatcher:
    """Watch vault directory for changes, debounce, and fan-out to async subscribers."""

    EXCLUDED: ClassVar[set[str]] = {
        ".obsidian",
        ".git",
        ".locks",
        "attachments",
        "__pycache__",
        ".trash",
    }

    def __init__(
        self,
        vault_path: str,
        loop: asyncio.AbstractEventLoop,
        debounce_seconds: float = 1.0,
    ):
        self._vault_path = Path(vault_path).resolve()
        self._loop = loop
        self._debounce_seconds = debounce_seconds
        self._observer = Observer()
        self._subscribers: list[asyncio.Queue[VaultEvent]] = []
        self._lock = threading.Lock()
        self._timers: dict[tuple[str, str], threading.Timer] = {}
        self._started = False

    def start(self) -> None:
        """Start watching the vault directory."""
        handler = _VaultEventHandler(self)
        self._observer.schedule(handler, str(self._vault_path), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        self._started = True
        logger.info("VaultFileWatcher started: %s", self._vault_path)

    def stop(self) -> None:
        """Stop watching and clean up."""
        if self._started:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._started = False
            # Cancel pending timers
            with self._lock:
                for timer in self._timers.values():
                    timer.cancel()
                self._timers.clear()
            logger.info("VaultFileWatcher stopped")

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue[VaultEvent]:
        """Add a subscriber queue with bounded size. Returns the queue.

        Args:
            maxsize: Maximum queue size (default 1000 events)

        Returns:
            asyncio.Queue with bounded size

        Security: Prevents unbounded queue growth (DoS mitigation)
        """
        queue: asyncio.Queue[VaultEvent] = asyncio.Queue(maxsize=maxsize)
        with self._lock:
            self._subscribers.append(queue)
        logger.debug(
            f"Subscriber added (queue maxsize={maxsize}, total={len(self._subscribers)})"
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be filtered out."""
        try:
            rel = path.relative_to(self._vault_path)
        except ValueError:
            return True

        # Check each component against exclusions
        for part in rel.parts:
            if part in self.EXCLUDED or part.startswith("."):
                return True

        # Only watch .md files
        if (path.is_file() or not path.exists()) and path.suffix != ".md":
            return True

        # Skip template files
        return path.name == "_template.md"

    def _on_event(
        self, event_type: str, src_path: str, dest_path: str | None = None
    ) -> None:
        """Handle a raw filesystem event with debouncing."""
        path = Path(src_path)
        if self._should_ignore(path):
            return

        try:
            rel_path = str(path.relative_to(self._vault_path))
        except ValueError:
            return

        old_path = None
        if dest_path:
            dest = Path(dest_path)
            if self._should_ignore(dest):
                return
            try:
                old_path = rel_path
                rel_path = str(dest.relative_to(self._vault_path))
            except ValueError:
                return

        key = (rel_path, event_type)

        with self._lock:
            # Cancel existing timer for this key
            if key in self._timers:
                self._timers[key].cancel()

            # Create new debounce timer
            timer = threading.Timer(
                self._debounce_seconds,
                self._emit_event,
                args=(event_type, rel_path, old_path),
            )
            timer.daemon = True
            self._timers[key] = timer
            timer.start()

    def _emit_event(self, event_type: str, path: str, old_path: str | None) -> None:
        """Emit event to all subscribers (called after debounce)."""
        event = VaultEvent(event_type=event_type, path=path, old_path=old_path)

        with self._lock:
            key = (path, event_type)
            self._timers.pop(key, None)
            subscribers = list(self._subscribers)

        for queue in subscribers:
            try:
                self._loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception:
                logger.debug("Failed to deliver event to subscriber", exc_info=True)


class _VaultEventHandler(FileSystemEventHandler):
    """Watchdog handler that delegates to VaultFileWatcher."""

    def __init__(self, watcher: VaultFileWatcher):
        self._watcher = watcher

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._watcher._on_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._watcher._on_event("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._watcher._on_event("deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._watcher._on_event("moved", event.src_path, event.dest_path)
