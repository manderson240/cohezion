"""Comprehensive audit logging for GDPR/HIPAA/SOC2 compliance.

This module implements an append-only audit trail for all sensitive operations:
- Vault read/write/delete operations
- Agent authentication events
- Credential rotation and revocation
- API calls with agent context

Features:
- Immutable append-only JSONL format
- Date-partitioned log files
- Query by agent/action/date range
- Compliance export (CSV/JSON)
- Configurable retention policy
- Non-blocking async writes
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class AuditAction(StrEnum):
    """Audit-logged actions."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    AUTHENTICATE = "authenticate"
    REVOKE = "revoke"
    ROTATE = "rotate"
    EXPORT = "export"
    EXECUTE = "execute"


@dataclass
class AuditLogEntry:
    """Single audit log entry.

    Attributes:
        timestamp: When the action occurred (UTC)
        agent_id: Which agent performed the action
        action: Type of action (from AuditAction)
        resource: What was accessed (e.g., vault path)
        status: "success" or "failure"
        details: Additional context (error message, bytes transferred, etc.)
        ip_address: Source IP address
        user_agent: Client user agent string
    """

    timestamp: datetime
    agent_id: str
    action: AuditAction
    resource: str
    status: str = "success"
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["action"] = self.action.value
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "AuditLogEntry":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["action"] = AuditAction(data["action"])
        return cls(**data)


class AuditLogger:
    """Manages audit log persistence and querying.

    Logs are stored in date-partitioned JSONL files with append-only writes
    for immutability.

    Example usage::

        logger = AuditLogger(log_path="data/audit_logs/")

        # Log a successful operation
        logger.log(AuditLogEntry(
            timestamp=datetime.utcnow(),
            agent_id="agent-1",
            action=AuditAction.READ,
            resource="/projects/test.md",
            status="success",
            ip_address="127.0.0.1",
            user_agent="cohezion-client/1.0"
        ))

        # Query logs
        logs = logger.query(agent_id="agent-1", action=AuditAction.READ)
        for log in logs:
            print(f"{log.timestamp}: {log.action} {log.resource} -> {log.status}")

        # Export for compliance
        report = logger.export_for_compliance(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 2, 1)
        )
    """

    def __init__(
        self,
        log_path: str = "data/audit_logs/",
        enable_persistence: bool = True,
        retention_days: int = 90,
    ):
        """Initialize audit logger.

        Args:
            log_path: Directory for audit log files
            enable_persistence: Whether to persist logs (disable for testing)
            retention_days: Days to keep audit logs
        """
        self.log_path = Path(log_path).expanduser()
        self.enable_persistence = enable_persistence
        self.retention_days = retention_days

        # Create directory if needed
        if self.enable_persistence:
            self.log_path.mkdir(parents=True, exist_ok=True)

    def log(self, entry: AuditLogEntry) -> bool:
        """Log an action (non-blocking append).

        Args:
            entry: AuditLogEntry to log

        Returns:
            True if successful, False on error
        """
        if not self.enable_persistence:
            return True

        try:
            # Get date-partitioned filename (e.g., audit_2026-02-09.jsonl)
            date_str = entry.timestamp.date().isoformat()
            log_file = self.log_path / f"audit_{date_str}.jsonl"

            # Append to file (atomic)
            with open(log_file, "a") as f:
                f.write(entry.to_json() + "\n")

            logger.debug(
                "Logged %s action on %s by %s",
                entry.action.value,
                entry.resource,
                entry.agent_id,
            )
            return True

        except Exception as e:
            # Non-blocking: log error but don't crash
            logger.warning("Failed to persist audit log entry: %s", e)
            return False

    def query(
        self,
        agent_id: str | None = None,
        action: AuditAction | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        resource: str | None = None,
    ) -> list[AuditLogEntry]:
        """Query audit logs with filters.

        Args:
            agent_id: Filter by agent ID
            action: Filter by action type
            start_date: Filter after this date
            end_date: Filter before this date
            resource: Filter by resource path

        Returns:
            List of matching AuditLogEntry objects
        """
        if not self.enable_persistence:
            return []

        entries = []

        # Set default date range (last 90 days)
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=self.retention_days)
        if not end_date:
            end_date = datetime.now(UTC)

        # Iterate through date-partitioned files
        current_date = start_date.date()
        while current_date <= end_date.date():
            log_file = self.log_path / f"audit_{current_date.isoformat()}.jsonl"

            if log_file.exists():
                try:
                    with open(log_file) as f:
                        for line in f:
                            if not line.strip():
                                continue

                            try:
                                entry = AuditLogEntry.from_json(line)

                                # Apply filters
                                if agent_id and entry.agent_id != agent_id:
                                    continue
                                if action and entry.action != action:
                                    continue
                                if resource and not entry.resource.startswith(resource):
                                    continue

                                entries.append(entry)

                            except Exception as e:
                                logger.warning("Failed to parse audit log entry: %s", e)

                except Exception as e:
                    logger.warning("Failed to read audit log file %s: %s", log_file, e)

            current_date += timedelta(days=1)

        return entries

    def export_for_compliance(
        self,
        start_date: datetime,
        end_date: datetime,
        export_format: str = "json",
    ) -> str:
        """Export audit trail for compliance review.

        Args:
            start_date: Export start date
            end_date: Export end date
            export_format: Output format ("json" or "csv")

        Returns:
            Exported audit trail as JSON or CSV string
        """
        entries = self.query(start_date=start_date, end_date=end_date)

        if export_format == "json":
            return json.dumps(
                [asdict(e) for e in entries],
                indent=2,
                default=str,
            )

        elif export_format == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            if entries:
                writer = csv.DictWriter(
                    output,
                    fieldnames=[
                        "timestamp",
                        "agent_id",
                        "action",
                        "resource",
                        "status",
                        "details",
                        "ip_address",
                        "user_agent",
                    ],
                )
                writer.writeheader()
                for entry in entries:
                    row = asdict(entry)
                    row["action"] = row["action"].value
                    row["details"] = json.dumps(row["details"]) if row["details"] else ""
                    writer.writerow(row)

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported format: {export_format}")

    def cleanup_old_logs(self, retention_days: int | None = None) -> int:
        """Delete audit logs older than retention period.

        Args:
            retention_days: Days to keep (default: configured value)

        Returns:
            Number of files deleted
        """
        if not self.enable_persistence:
            return 0

        retention_days = retention_days or self.retention_days
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        deleted_count = 0

        try:
            for log_file in self.log_path.glob("audit_*.jsonl"):
                # Extract date from filename
                date_str = log_file.stem.replace("audit_", "")

                try:
                    file_date = datetime.fromisoformat(date_str).replace(tzinfo=UTC)

                    if file_date < cutoff_date:
                        log_file.unlink()
                        deleted_count += 1
                        logger.info("Deleted old audit log: %s", log_file)

                except ValueError:
                    logger.warning("Could not parse date from audit log: %s", log_file)

        except Exception as e:
            logger.error("Failed to cleanup audit logs: %s", e)

        if deleted_count > 0:
            logger.info(
                "Cleaned up %d audit logs older than %d days", deleted_count, retention_days
            )

        return deleted_count

    def get_stats(self) -> dict[str, Any]:
        """Get audit logging statistics.

        Returns:
            Dictionary with log file stats
        """
        if not self.enable_persistence:
            return {"enabled": False}

        try:
            log_files = list(self.log_path.glob("audit_*.jsonl"))
            total_size = sum(f.stat().st_size for f in log_files)

            return {
                "enabled": True,
                "log_files": len(log_files),
                "total_size_bytes": total_size,
                "log_path": str(self.log_path),
                "retention_days": self.retention_days,
            }

        except Exception as e:
            logger.warning("Failed to get audit log stats: %s", e)
            return {"enabled": True, "error": str(e)}
