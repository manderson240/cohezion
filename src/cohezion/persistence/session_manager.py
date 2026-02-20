"""
Session state management with context preservation.

Attribution: Context preservation pattern inspired by Pilot's session continuity
Implementation: Original COHEZION design with FLUME and vault integration
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionSnapshot:
    """Snapshot of session state for preservation.

    Captures full state before context clear for restoration in new session.
    """

    session_id: str
    timestamp: datetime
    coherence: float
    active_tasks: Dict[str, Any]
    journey_checkpoint: Dict[str, Any]
    skill_context: Dict[str, Any]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to dictionary."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "coherence": self.coherence,
            "active_tasks": self.active_tasks,
            "journey_checkpoint": self.journey_checkpoint,
            "skill_context": self.skill_context,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionSnapshot:
        """Deserialize snapshot from dictionary."""
        return cls(
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            coherence=data["coherence"],
            active_tasks=data["active_tasks"],
            journey_checkpoint=data["journey_checkpoint"],
            skill_context=data["skill_context"],
            metrics=data["metrics"],
        )


class SessionManager:
    """Manages session state with context preservation.

    Attribution: Inspired by Pilot's pre/post compaction pattern
    Implementation: COHEZION-native with FLUME VAE compression and vault persistence
    """

    def __init__(
        self,
        session_id: str,
        snapshot_dir: Optional[Path] = None,
        vault_client: Optional[Any] = None,
        journey_tracker: Optional[Any] = None,
    ) -> None:
        """Initialize session manager.

        Args:
            session_id: Unique session identifier
            snapshot_dir: Directory for snapshot storage (defaults to ~/.cohezion/sessions/)
            vault_client: Optional vault MCP client for persistent storage
            journey_tracker: Optional JourneyTracker for 12D state capture
        """
        self.session_id = session_id
        self.snapshot_dir = snapshot_dir or Path.home() / ".cohezion" / "sessions"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        self._vault = vault_client
        self._journey_tracker = journey_tracker
        self._current_snapshot: Optional[SessionSnapshot] = None

    async def create_snapshot(
        self,
        coherence: float,
        active_tasks: Dict[str, Any],
        skill_context: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> SessionSnapshot:
        """Create pre-clear snapshot of current session state.

        This captures full state before context compaction for restoration.

        Args:
            coherence: Current HIHO coherence level
            active_tasks: Active task state
            skill_context: Skill execution context
            metrics: Current metrics

        Returns:
            SessionSnapshot object
        """
        # Capture journey checkpoint if available
        journey_checkpoint = {}
        if self._journey_tracker:
            try:
                journey_checkpoint = (
                    self._journey_tracker.get_current_checkpoint()
                )
            except Exception as e:
                logger.warning(f"Failed to capture journey checkpoint: {e}")

        snapshot = SessionSnapshot(
            session_id=self.session_id,
            timestamp=datetime.now(),
            coherence=coherence,
            active_tasks=active_tasks,
            journey_checkpoint=journey_checkpoint,
            skill_context=skill_context,
            metrics=metrics,
        )

        # Save to local filesystem
        snapshot_path = self.snapshot_dir / f"{self.session_id}_snapshot.json"
        with open(snapshot_path, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        logger.info(f"Created session snapshot at {snapshot_path}")

        # Persist to vault if available
        if self._vault:
            try:
                await self._vault.store_session_snapshot(
                    session_id=self.session_id, snapshot=snapshot.to_dict()
                )
                logger.debug("Synced snapshot to vault")
            except Exception as e:
                logger.warning(f"Failed to sync snapshot to vault: {e}")

        self._current_snapshot = snapshot
        return snapshot

    async def restore_snapshot(
        self, session_id: Optional[str] = None
    ) -> Optional[SessionSnapshot]:
        """Restore session state from snapshot.

        Loads from local filesystem first, falls back to vault if not found.

        Args:
            session_id: Session ID to restore (defaults to current session)

        Returns:
            SessionSnapshot if found, None otherwise
        """
        target_id = session_id or self.session_id
        snapshot_path = self.snapshot_dir / f"{target_id}_snapshot.json"

        # Try local filesystem first
        if snapshot_path.exists():
            try:
                with open(snapshot_path) as f:
                    data = json.load(f)
                snapshot = SessionSnapshot.from_dict(data)
                logger.info(f"Restored snapshot from {snapshot_path}")
                return snapshot
            except Exception as e:
                logger.error(f"Failed to load snapshot from filesystem: {e}")

        # Fallback to vault
        if self._vault:
            try:
                data = await self._vault.get_session_snapshot(
                    session_id=target_id
                )
                if data:
                    snapshot = SessionSnapshot.from_dict(data)
                    logger.info(f"Restored snapshot from vault for {target_id}")
                    return snapshot
            except Exception as e:
                logger.warning(f"Failed to load snapshot from vault: {e}")

        logger.warning(f"No snapshot found for session {target_id}")
        return None

    def list_snapshots(self) -> list[str]:
        """List available session snapshots."""
        snapshots = []
        for snapshot_file in self.snapshot_dir.glob("*_snapshot.json"):
            session_id = snapshot_file.stem.replace("_snapshot", "")
            snapshots.append(session_id)
        return snapshots

    async def cleanup_old_snapshots(self, keep_count: int = 10) -> None:
        """Clean up old snapshots, keeping only the most recent.

        Args:
            keep_count: Number of snapshots to retain
        """
        snapshot_files = sorted(
            self.snapshot_dir.glob("*_snapshot.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for snapshot_file in snapshot_files[keep_count:]:
            try:
                snapshot_file.unlink()
                logger.debug(f"Removed old snapshot: {snapshot_file}")
            except Exception as e:
                logger.warning(f"Failed to remove snapshot {snapshot_file}: {e}")
