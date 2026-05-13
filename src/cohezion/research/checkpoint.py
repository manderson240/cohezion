"""Checkpoint persistence for ResearchAgent.

Elegant integration with Cohezion's vault storage via MCP.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ResearchCheckpoint:
    """Complete checkpoint for research session state.

    Serializable to JSON for vault storage.
    """

    session_id: str
    experiments_completed: int
    best_metric: float
    best_checkpoint_path: str | None
    experiment_log_path: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "experiments_completed": self.experiments_completed,
            "best_metric": self.best_metric if self.best_metric != float("inf") else None,
            "best_checkpoint_path": self.best_checkpoint_path,
            "experiment_log_path": self.experiment_log_path,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchCheckpoint:
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            experiments_completed=data["experiments_completed"],
            best_metric=data.get("best_metric") or float("inf"),
            best_checkpoint_path=data.get("best_checkpoint_path"),
            experiment_log_path=data["experiment_log_path"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


class CheckpointPersistence:
    """Handles checkpoint persistence to vault and local storage.

    Primary: MCP vault via mcp.vault_write/read
    Fallback: Local JSON in data/research/checkpoints/
    """

    def __init__(
        self,
        mcp_client: Any | None = None,
        local_dir: Path | None = None,
    ):
        """Initialize persistence layer.

        Args:
            mcp_client: MCP client for vault operations
            local_dir: Directory for local fallback storage
        """
        self.mcp_client = mcp_client
        self.local_dir = local_dir or Path("data/research/checkpoints")
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        session_id: str,
        experiments_completed: int,
        best_metric: float,
        best_checkpoint_path: Path | None,
        experiment_log_path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save checkpoint to vault and local storage.

        Args:
            session_id: Unique session identifier
            experiments_completed: Number of experiments done
            best_metric: Best metric achieved
            best_checkpoint_path: Path to best checkpoint file
            experiment_log_path: Path to experiment log
            metadata: Optional additional metadata

        Returns:
            Checkpoint ID (session_id)
        """
        checkpoint = ResearchCheckpoint(
            session_id=session_id,
            experiments_completed=experiments_completed,
            best_metric=best_metric,
            best_checkpoint_path=str(best_checkpoint_path) if best_checkpoint_path else None,
            experiment_log_path=str(experiment_log_path),
            metadata=metadata or {},
        )

        # Save to vault (primary)
        if self.mcp_client:
            try:
                checkpoint_data = json.dumps(checkpoint.to_dict())
                vault_path = f"research/checkpoints/{session_id}.json"
                self.mcp_client.vault_write(vault_path, checkpoint_data)
                logger.info(f"Checkpoint saved to vault: {vault_path}")
            except Exception as e:
                logger.warning(f"Failed to save checkpoint to vault: {e}")

        # Save locally (fallback)
        local_path = self.local_dir / f"{session_id}.json"
        try:
            with open(local_path, "w") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
            logger.info(f"Checkpoint saved locally: {local_path}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint locally: {e}")

        return session_id

    def load_checkpoint(self, session_id: str) -> ResearchCheckpoint | None:
        """Load checkpoint from vault or local storage.

        Args:
            session_id: Session identifier

        Returns:
            Checkpoint or None if not found
        """
        # Try vault first
        if self.mcp_client:
            try:
                vault_path = f"research/checkpoints/{session_id}.json"
                data = self.mcp_client.vault_read(vault_path)
                if data:
                    checkpoint_dict = json.loads(data)
                    logger.info(f"Checkpoint loaded from vault: {vault_path}")
                    return ResearchCheckpoint.from_dict(checkpoint_dict)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint from vault: {e}")

        # Fallback to local
        local_path = self.local_dir / f"{session_id}.json"
        try:
            with open(local_path) as f:
                checkpoint_dict = json.load(f)
            logger.info(f"Checkpoint loaded locally: {local_path}")
            return ResearchCheckpoint.from_dict(checkpoint_dict)
        except FileNotFoundError:
            logger.warning(f"Checkpoint not found: {local_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def list_checkpoints(self) -> list[str]:
        """List all available checkpoint session IDs.

        Returns:
            List of session IDs
        """
        session_ids = []

        # List local checkpoints
        try:
            for checkpoint_file in self.local_dir.glob("*.json"):
                session_ids.append(checkpoint_file.stem)
        except Exception as e:
            logger.warning(f"Failed to list local checkpoints: {e}")

        return session_ids

    def delete_checkpoint(self, session_id: str) -> bool:
        """Delete checkpoint from vault and local storage.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted successfully
        """
        deleted = False

        # Delete from vault
        if self.mcp_client:
            try:
                vault_path = f"research/checkpoints/{session_id}.json"
                self.mcp_client.vault_delete(vault_path)
                deleted = True
                logger.info(f"Checkpoint deleted from vault: {vault_path}")
            except Exception as e:
                logger.warning(f"Failed to delete checkpoint from vault: {e}")

        # Delete locally
        local_path = self.local_dir / f"{session_id}.json"
        try:
            local_path.unlink()
            deleted = True
            logger.info(f"Checkpoint deleted locally: {local_path}")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to delete checkpoint locally: {e}")

        return deleted


class WarmCheckpointLoader:
    """Loads checkpoints into ResearchAgent on startup.

    Restores session state from previous checkpoint.
    """

    def __init__(self, persistence: CheckpointPersistence):
        """Initialize with persistence layer."""
        self.persistence = persistence

    def restore_session(
        self,
        session_id: str,
        agent: Any,
    ) -> bool:
        """Restore agent session from checkpoint.

        Args:
            session_id: Session to restore
            agent: ResearchAgent instance to update

        Returns:
            True if restored successfully
        """
        checkpoint = self.persistence.load_checkpoint(session_id)
        if not checkpoint:
            logger.warning(f"No checkpoint found for session: {session_id}")
            return False

        # Restore session state
        agent.session.experiments_completed = checkpoint.experiments_completed
        agent.session.best_metric = checkpoint.best_metric
        if checkpoint.best_checkpoint_path:
            agent.session.best_checkpoint = Path(checkpoint.best_checkpoint_path)

        logger.info(
            f"Session restored from checkpoint: {session_id} ({checkpoint.experiments_completed} experiments completed)"
        )
        return True

    def list_available_sessions(self) -> list[dict[str, Any]]:
        """List sessions with available checkpoints.

        Returns:
            List of session info dicts
        """
        sessions = []
        for session_id in self.persistence.list_checkpoints():
            checkpoint = self.persistence.load_checkpoint(session_id)
            if checkpoint:
                sessions.append(
                    {
                        "session_id": checkpoint.session_id,
                        "experiments_completed": checkpoint.experiments_completed,
                        "best_metric": checkpoint.best_metric,
                        "timestamp": checkpoint.timestamp,
                    }
                )
        return sessions
