"""Configuration sync logging to SurrealDB - Phase 3.

Tracks all configuration operations (validation, sync, archival)
for audit trail and state recovery.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class SyncLogEntry:
    """Log entry for a sync operation."""

    timestamp: str
    operation: str  # "validate", "sync", "archive", "conflict"
    status: str  # "success", "failed", "warning"
    file: str
    details: dict[str, Any]
    duration_ms: float = 0.0
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)


class ConfigSyncLogger:
    """Logs configuration operations for audit and recovery."""

    def __init__(
        self,
        log_dir: Path | None = None,
    ):
        """Initialize sync logger."""
        if log_dir is None:
            log_dir = Path.cwd() / "data" / "config-sync-logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # In-memory log for session
        self._entries: list[SyncLogEntry] = []

    async def log_validation(
        self,
        file: str,
        status: str,
        details: dict[str, Any],
        duration_ms: float = 0.0,
        error_message: str | None = None,
    ) -> None:
        """Log a validation operation."""
        entry = SyncLogEntry(
            timestamp=datetime.now().isoformat(),
            operation="validate",
            status=status,
            file=file,
            details=details,
            duration_ms=duration_ms,
            error_message=error_message,
        )

        self._entries.append(entry)
        await self._persist_entry(entry)

        level = "error" if status == "failed" else "info"
        getattr(logger, level)(f"Validation {status}: {file} ({duration_ms:.1f}ms)")

    async def log_sync(
        self,
        file: str,
        status: str,
        details: dict[str, Any],
        duration_ms: float = 0.0,
        error_message: str | None = None,
    ) -> None:
        """Log a sync operation."""
        entry = SyncLogEntry(
            timestamp=datetime.now().isoformat(),
            operation="sync",
            status=status,
            file=file,
            details=details,
            duration_ms=duration_ms,
            error_message=error_message,
        )

        self._entries.append(entry)
        await self._persist_entry(entry)

        logger.info(f"Sync {status}: {file} ({duration_ms:.1f}ms)")

    async def log_archival(
        self,
        file: str,
        status: str,
        details: dict[str, Any],
        duration_ms: float = 0.0,
    ) -> None:
        """Log an archival operation."""
        entry = SyncLogEntry(
            timestamp=datetime.now().isoformat(),
            operation="archive",
            status=status,
            file=file,
            details=details,
            duration_ms=duration_ms,
        )

        self._entries.append(entry)
        await self._persist_entry(entry)

        logger.info(f"Archive {status}: {file} ({duration_ms:.1f}ms)")

    async def log_conflict(
        self,
        file: str,
        details: dict[str, Any],
    ) -> None:
        """Log a conflict detection."""
        entry = SyncLogEntry(
            timestamp=datetime.now().isoformat(),
            operation="conflict",
            status="detected",
            file=file,
            details=details,
        )

        self._entries.append(entry)
        await self._persist_entry(entry)

        logger.warning(f"Conflict detected in {file}")

    async def _persist_entry(self, entry: SyncLogEntry) -> None:
        """Persist log entry to disk."""
        try:
            # Append to JSONL log file
            log_file = self.log_dir / "config_sync.jsonl"

            with open(log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")

        except Exception as e:
            logger.warning(f"Failed to persist log entry: {e}")

    def get_recent_logs(self, limit: int = 50) -> list[SyncLogEntry]:
        """Get recent log entries."""
        return self._entries[-limit:]

    def get_logs_by_operation(self, operation: str) -> list[SyncLogEntry]:
        """Get logs filtered by operation type."""
        return [e for e in self._entries if e.operation == operation]

    def get_logs_by_status(self, status: str) -> list[SyncLogEntry]:
        """Get logs filtered by status."""
        return [e for e in self._entries if e.status == status]

    def get_logs_by_file(self, file: str) -> list[SyncLogEntry]:
        """Get logs for specific file."""
        return [e for e in self._entries if e.file == file]

    def export_to_json(self, output_path: Path | None = None) -> str:
        """Export all logs to JSON."""
        if output_path is None:
            output_path = (
                self.log_dir / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        data = {
            "exported_at": datetime.now().isoformat(),
            "entry_count": len(self._entries),
            "entries": [e.to_dict() for e in self._entries],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported {len(self._entries)} logs to {output_path}")

        return str(output_path)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about logged operations."""
        if not self._entries:
            return {"total_entries": 0}

        operations = {}
        statuses = {}
        files = {}

        for entry in self._entries:
            operations[entry.operation] = operations.get(entry.operation, 0) + 1
            statuses[entry.status] = statuses.get(entry.status, 0) + 1
            files[entry.file] = files.get(entry.file, 0) + 1

        total_duration = sum(e.duration_ms for e in self._entries)
        avg_duration = total_duration / len(self._entries) if self._entries else 0

        return {
            "total_entries": len(self._entries),
            "by_operation": operations,
            "by_status": statuses,
            "by_file": files,
            "total_duration_ms": total_duration,
            "average_duration_ms": avg_duration,
            "failure_count": statuses.get("failed", 0),
            "success_rate": (statuses.get("success", 0) / len(self._entries) * 100 if self._entries else 0),
        }
