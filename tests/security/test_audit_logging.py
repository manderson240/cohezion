"""Tests for audit logging (Task #3: Phase 2 Security)."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cohezion.security.audit_log import (
    AuditAction,
    AuditLogEntry,
    AuditLogger,
)


@pytest.fixture
def audit_logger(tmp_path):
    """Create test audit logger."""
    log_path = tmp_path / "audit_logs"
    return AuditLogger(log_path=str(log_path), enable_persistence=True)


@pytest.fixture
def audit_logger_no_persist():
    """Create audit logger without persistence."""
    return AuditLogger(enable_persistence=False)


class TestAuditLogEntry:
    """Tests for AuditLogEntry dataclass."""

    def test_entry_creation(self):
        """Test creating audit log entry."""
        now = datetime.now(UTC)
        entry = AuditLogEntry(
            timestamp=now,
            agent_id="agent-1",
            action=AuditAction.READ,
            resource="/projects/test.md",
            status="success",
        )

        assert entry.agent_id == "agent-1"
        assert entry.action == AuditAction.READ
        assert entry.resource == "/projects/test.md"
        assert entry.status == "success"

    def test_entry_to_json(self):
        """Test serialization to JSON."""
        now = datetime.now(UTC)
        entry = AuditLogEntry(
            timestamp=now,
            agent_id="agent-1",
            action=AuditAction.WRITE,
            resource="/data/test.json",
            status="success",
            details={"bytes": 1024},
        )

        json_str = entry.to_json()
        data = json.loads(json_str)

        assert data["agent_id"] == "agent-1"
        assert data["action"] == "write"
        assert data["resource"] == "/data/test.json"
        assert data["details"]["bytes"] == 1024

    def test_entry_from_json(self):
        """Test deserialization from JSON."""
        now = datetime.now(UTC)
        original = AuditLogEntry(
            timestamp=now,
            agent_id="agent-2",
            action=AuditAction.DELETE,
            resource="/archive/old.md",
            status="failure",
            details={"error": "Permission denied"},
        )

        json_str = original.to_json()
        deserialized = AuditLogEntry.from_json(json_str)

        assert deserialized.agent_id == original.agent_id
        assert deserialized.action == original.action
        assert deserialized.resource == original.resource
        assert deserialized.status == original.status


class TestAuditLoggerBasics:
    """Tests for basic AuditLogger functionality."""

    def test_log_entry(self, audit_logger):
        """Test logging an entry."""
        entry = AuditLogEntry(
            timestamp=datetime.now(UTC),
            agent_id="agent-1",
            action=AuditAction.READ,
            resource="/projects/test.md",
            status="success",
        )

        result = audit_logger.log(entry)
        assert result is True

    def test_log_creates_file(self, audit_logger, tmp_path):
        """Test that logging creates date-partitioned file."""
        entry = AuditLogEntry(
            timestamp=datetime.now(UTC),
            agent_id="agent-1",
            action=AuditAction.WRITE,
            resource="/data/test.json",
        )

        audit_logger.log(entry)

        # Check file was created
        log_files = list(Path(audit_logger.log_path).glob("audit_*.jsonl"))
        assert len(log_files) > 0

    def test_log_without_persistence(self, audit_logger_no_persist):
        """Test logging with persistence disabled."""
        entry = AuditLogEntry(
            timestamp=datetime.now(UTC),
            agent_id="agent-1",
            action=AuditAction.READ,
            resource="/test",
        )

        result = audit_logger_no_persist.log(entry)
        assert result is True

    def test_multiple_entries_same_day(self, audit_logger):
        """Test logging multiple entries to same file."""
        now = datetime.now(UTC)

        for i in range(3):
            entry = AuditLogEntry(
                timestamp=now,
                agent_id=f"agent-{i}",
                action=AuditAction.READ,
                resource=f"/test/{i}",
            )
            audit_logger.log(entry)

        # Check only one file created
        log_files = list(Path(audit_logger.log_path).glob("audit_*.jsonl"))
        assert len(log_files) == 1

        # Check file contains 3 lines
        with open(log_files[0]) as f:
            lines = f.readlines()
            assert len(lines) == 3


class TestAuditLoggerQuery:
    """Tests for querying audit logs."""

    def test_query_by_agent_id(self, audit_logger):
        """Test querying logs by agent ID."""
        now = datetime.now(UTC)

        # Log entries from different agents
        for i in range(3):
            entry = AuditLogEntry(
                timestamp=now,
                agent_id="agent-1" if i < 2 else "agent-2",
                action=AuditAction.READ,
                resource=f"/test/{i}",
            )
            audit_logger.log(entry)

        # Query for agent-1
        results = audit_logger.query(agent_id="agent-1")
        assert len(results) == 2
        assert all(r.agent_id == "agent-1" for r in results)

    def test_query_by_action(self, audit_logger):
        """Test querying logs by action type."""
        now = datetime.now(UTC)

        actions = [
            AuditAction.READ,
            AuditAction.READ,
            AuditAction.WRITE,
            AuditAction.DELETE,
        ]

        for action in actions:
            entry = AuditLogEntry(
                timestamp=now,
                agent_id="agent-1",
                action=action,
                resource="/test",
            )
            audit_logger.log(entry)

        # Query for reads
        results = audit_logger.query(action=AuditAction.READ)
        assert len(results) == 2

        # Query for writes
        results = audit_logger.query(action=AuditAction.WRITE)
        assert len(results) == 1

    def test_query_by_date_range(self, audit_logger):
        """Test querying logs by date range."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Log entries
        entry = AuditLogEntry(
            timestamp=now,
            agent_id="agent-1",
            action=AuditAction.READ,
            resource="/test",
        )
        audit_logger.log(entry)

        # Query includes today
        results = audit_logger.query(start_date=yesterday, end_date=tomorrow)
        assert len(results) >= 1

        # Query excludes today
        results = audit_logger.query(
            start_date=tomorrow,
            end_date=tomorrow + timedelta(days=1),
        )
        assert len(results) == 0

    def test_query_by_resource(self, audit_logger):
        """Test querying logs by resource path."""
        now = datetime.now(UTC)

        resources = ["/projects/test.md", "/data/test.json", "/archive/old.md"]
        for resource in resources:
            entry = AuditLogEntry(
                timestamp=now,
                agent_id="agent-1",
                action=AuditAction.READ,
                resource=resource,
            )
            audit_logger.log(entry)

        # Query for projects
        results = audit_logger.query(resource="/projects")
        assert len(results) == 1
        assert results[0].resource == "/projects/test.md"

    def test_query_combined_filters(self, audit_logger):
        """Test querying with multiple filters."""
        now = datetime.now(UTC)

        entries_data = [
            ("agent-1", AuditAction.READ, "/projects/a.md"),
            ("agent-1", AuditAction.WRITE, "/projects/b.md"),
            ("agent-2", AuditAction.READ, "/data/c.json"),
        ]

        for agent_id, action, resource in entries_data:
            entry = AuditLogEntry(
                timestamp=now,
                agent_id=agent_id,
                action=action,
                resource=resource,
            )
            audit_logger.log(entry)

        # Query for agent-1 reads
        results = audit_logger.query(agent_id="agent-1", action=AuditAction.READ)
        assert len(results) == 1
        assert results[0].resource == "/projects/a.md"


class TestAuditLoggerExport:
    """Tests for compliance export."""

    def test_export_json(self, audit_logger):
        """Test exporting logs as JSON."""
        now = datetime.now(UTC)

        entry = AuditLogEntry(
            timestamp=now,
            agent_id="agent-1",
            action=AuditAction.READ,
            resource="/test.md",
            status="success",
        )
        audit_logger.log(entry)

        # Export as JSON
        json_export = audit_logger.export_for_compliance(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            export_format="json",
        )

        data = json.loads(json_export)
        assert len(data) >= 1
        assert data[0]["agent_id"] == "agent-1"

    def test_export_csv(self, audit_logger):
        """Test exporting logs as CSV."""
        now = datetime.now(UTC)

        entry = AuditLogEntry(
            timestamp=now,
            agent_id="agent-1",
            action=AuditAction.WRITE,
            resource="/data.json",
            status="success",
        )
        audit_logger.log(entry)

        # Export as CSV
        csv_export = audit_logger.export_for_compliance(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            export_format="csv",
        )

        assert "agent-1" in csv_export
        assert "write" in csv_export
        assert "/data.json" in csv_export

    def test_export_invalid_format(self, audit_logger):
        """Test export with invalid format raises error."""
        now = datetime.now(UTC)

        with pytest.raises(ValueError, match="Unsupported format"):
            audit_logger.export_for_compliance(
                start_date=now,
                end_date=now,
                export_format="xml",
            )


class TestAuditLoggerCleanup:
    """Tests for cleanup of old logs."""

    def test_cleanup_old_logs(self, audit_logger):
        """Test removing old audit logs."""
        now = datetime.now(UTC)
        old_date = now - timedelta(days=100)

        # Log old entry
        old_entry = AuditLogEntry(
            timestamp=old_date,
            agent_id="agent-old",
            action=AuditAction.READ,
            resource="/old",
        )
        audit_logger.log(old_entry)

        # Log recent entry
        recent_entry = AuditLogEntry(
            timestamp=now,
            agent_id="agent-new",
            action=AuditAction.READ,
            resource="/new",
        )
        audit_logger.log(recent_entry)

        # Cleanup with 90-day retention
        deleted = audit_logger.cleanup_old_logs(retention_days=90)

        assert deleted == 1

        # Recent log should still exist
        results = audit_logger.query(agent_id="agent-new")
        assert len(results) >= 1


class TestAuditLoggerStats:
    """Tests for audit logger statistics."""

    def test_get_stats(self, audit_logger):
        """Test getting audit logger stats."""
        now = datetime.now(UTC)

        # Log some entries
        for i in range(3):
            entry = AuditLogEntry(
                timestamp=now,
                agent_id=f"agent-{i}",
                action=AuditAction.READ,
                resource=f"/test/{i}",
            )
            audit_logger.log(entry)

        stats = audit_logger.get_stats()

        assert stats["enabled"] is True
        assert stats["log_files"] >= 1
        assert stats["total_size_bytes"] > 0
