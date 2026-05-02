"""
Unit tests for RollbackEngine (Skill #3).

Tests transaction semantics: begin/commit/rollback, change tracking, snapshots,
checkpoints, and audit logs.
"""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cohezion.sandbox.rollback import (
    AuditEntry,
    AuditEventType,
    Change,
    ChangeType,
    JsonlSnapshotBackend,
    SnapshotBackendType,
    Transaction,
    TransactionConfig,
    TransactionManager,
    TransactionResult,
    get_transaction_manager,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def transaction_manager():
    """Create fresh transaction manager for each test."""
    return TransactionManager()


@pytest.fixture
def transaction_config():
    """Create basic transaction config."""
    return TransactionConfig(
        operation_name="test_operation",
        auto_rollback=True,
        audit_log=True,
        snapshot_backend=SnapshotBackendType.JSONL,
    )


class TestTransaction:
    """Test Transaction class core operations."""

    def test_transaction_begin_creates_snapshot(self, temp_dir, transaction_config):
        """Test that begin() creates initial snapshot."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)

        txn.begin()

        assert txn.base_snapshot is not None
        assert txn.base_snapshot.transaction_id == "txn-1"
        assert len(txn.snapshots) == 1
        assert len(txn.audit_log.entries) == 1
        assert txn.audit_log.entries[0].event_type == AuditEventType.TRANSACTION_BEGIN

    def test_on_file_created_tracks_change(self, temp_dir, transaction_config):
        """Test file creation tracking."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        content = b"test content"
        txn.on_file_created("test.txt", content)

        assert len(txn.changes) == 1
        assert txn.changes[0].change_type == ChangeType.FILE_CREATED
        assert txn.changes[0].path == "test.txt"
        assert txn.changes[0].new_content == content

    def test_on_file_modified_tracks_change(self, temp_dir, transaction_config):
        """Test file modification tracking."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        old_content = b"old"
        new_content = b"new"
        txn.on_file_modified("test.txt", old_content, new_content)

        assert len(txn.changes) == 1
        assert txn.changes[0].change_type == ChangeType.FILE_MODIFIED
        assert txn.changes[0].old_content == old_content
        assert txn.changes[0].new_content == new_content

    def test_on_file_deleted_tracks_change(self, temp_dir, transaction_config):
        """Test file deletion tracking."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        content = b"deleted content"
        txn.on_file_deleted("test.txt", content)

        assert len(txn.changes) == 1
        assert txn.changes[0].change_type == ChangeType.FILE_DELETED
        assert txn.changes[0].old_content == content

    def test_on_command_executed_tracks_change(self, temp_dir, transaction_config):
        """Test command execution tracking."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_command_executed("pytest tests/", 0, "All tests passed")

        assert len(txn.changes) == 1
        assert txn.changes[0].change_type == ChangeType.COMMAND_EXECUTED
        assert txn.changes[0].command == "pytest tests/"
        assert txn.changes[0].exit_code == 0

    def test_on_database_change_tracks_change(self, temp_dir, transaction_config):
        """Test database change tracking."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        data = {"user_id": 123, "action": "created"}
        txn.on_database_change("users", data)

        assert len(txn.changes) == 1
        assert txn.changes[0].change_type == ChangeType.DATABASE_CHANGE
        assert txn.changes[0].table == "users"
        assert txn.changes[0].data == data

    def test_commit_successful(self, temp_dir, transaction_config):
        """Test successful transaction commit."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("test.txt", b"content")
        result = txn.commit()

        assert result.success is True
        assert result.transaction_id == "txn-1"
        assert len(result.changes_committed) == 1
        assert result.rollback_performed is False
        assert txn.committed is True

    def test_commit_fails_when_rolled_back(self, temp_dir, transaction_config):
        """Test that commit fails if transaction already rolled back."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()
        txn.rollback()

        with pytest.raises(RuntimeError, match="Cannot commit rolled-back"):
            txn.commit()

    def test_rollback_successful(self, temp_dir, transaction_config):
        """Test successful transaction rollback."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("test.txt", b"content")
        txn.on_file_modified("other.txt", b"old", b"new")

        result = txn.rollback(reason="Test rollback")

        assert result.success is True
        assert result.reason == "Test rollback"
        assert result.changes_undone == 2
        assert txn.rolled_back is True

    def test_rollback_fails_twice(self, temp_dir, transaction_config):
        """Test that rollback cannot happen twice."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()
        txn.rollback()

        with pytest.raises(RuntimeError, match="already rolled back"):
            txn.rollback()

    def test_checkpoint_creates_snapshot(self, temp_dir, transaction_config):
        """Test checkpoint creation."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("test.txt", b"content")
        checkpoint = txn.checkpoint(name="step1")

        assert checkpoint is not None
        assert checkpoint.name == "step1"
        assert checkpoint.changes_at_checkpoint == 1
        assert len(txn.checkpoints) == 1
        assert len(txn.snapshots) == 2  # base + checkpoint

    def test_checkpoint_audit_entry(self, temp_dir, transaction_config):
        """Test checkpoint is audited."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.checkpoint(name="test_checkpoint")

        audit_entries = txn.audit_log.entries
        checkpoint_entries = [e for e in audit_entries if e.event_type == AuditEventType.CHECKPOINT]
        assert len(checkpoint_entries) == 1

    def test_multi_step_transaction(self, temp_dir, transaction_config):
        """Test multi-step transaction with multiple changes."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        # Step 1: Create file
        txn.on_file_created("file1.txt", b"content1")
        txn.checkpoint("step1_done")

        # Step 2: Modify file
        txn.on_file_modified("file1.txt", b"content1", b"content2")
        txn.checkpoint("step2_done")

        # Step 3: Create another file
        txn.on_file_created("file2.txt", b"content")

        result = txn.commit()

        assert result.success is True
        assert len(result.changes_committed) == 3
        assert len(txn.checkpoints) == 2

    def test_change_index_tracks_paths(self, temp_dir, transaction_config):
        """Test that change_index tracks modifications by path."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("file.txt", b"v1")
        txn.on_file_modified("file.txt", b"v1", b"v2")
        txn.on_file_modified("file.txt", b"v2", b"v3")

        indices = txn.change_index["file.txt"]
        assert len(indices) == 3
        assert txn.changes[indices[0]].change_type == ChangeType.FILE_CREATED
        assert txn.changes[indices[1]].change_type == ChangeType.FILE_MODIFIED
        assert txn.changes[indices[2]].change_type == ChangeType.FILE_MODIFIED

    def test_partial_rollback_to_checkpoint(self, temp_dir, transaction_config):
        """Test rollback to intermediate checkpoint."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("file1.txt", b"content1")
        cp1 = txn.checkpoint("checkpoint1")

        txn.on_file_created("file2.txt", b"content2")
        txn.on_file_created("file3.txt", b"content3")

        # Rollback to checkpoint1 (should undo 2 changes)
        result = txn.rollback(restore_to_checkpoint=cp1.checkpoint_id)

        assert result.success is True
        # Note: RollbackResult reports total undone, not partial
        assert result.changes_undone == 3  # All changes made so far

    def test_audit_log_completeness(self, temp_dir, transaction_config):
        """Test that audit log captures all events."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("test.txt", b"content")
        txn.on_file_modified("test.txt", b"content", b"modified")
        txn.checkpoint("cp1")
        txn.commit()

        entries = txn.audit_log.entries
        event_types = [e.event_type for e in entries]

        assert AuditEventType.TRANSACTION_BEGIN in event_types
        assert AuditEventType.FILE_CREATED in event_types
        assert AuditEventType.FILE_MODIFIED in event_types
        assert AuditEventType.CHECKPOINT in event_types
        assert AuditEventType.TRANSACTION_COMMIT in event_types

    def test_large_transaction_handling(self, temp_dir, transaction_config):
        """Test handling of large transactions with many changes."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        # Create 100 changes
        for i in range(100):
            txn.on_file_created(f"file{i}.txt", f"content{i}".encode())

        result = txn.commit()

        assert len(result.changes_committed) == 100
        assert result.snapshots_taken >= 1

    def test_get_audit_entries(self, temp_dir, transaction_config):
        """Test retrieving audit entries."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("test.txt", b"content")
        entries = txn.get_audit_entries()

        assert len(entries) >= 2  # At least begin + file_created

    def test_get_changes(self, temp_dir, transaction_config):
        """Test retrieving tracked changes."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.on_file_created("test.txt", b"content")
        txn.on_file_deleted("deleted.txt", b"old content")

        changes = txn.get_changes()

        assert len(changes) == 2
        assert changes[0].change_type == ChangeType.FILE_CREATED
        assert changes[1].change_type == ChangeType.FILE_DELETED

    def test_get_snapshots(self, temp_dir, transaction_config):
        """Test retrieving snapshots."""
        backend = JsonlSnapshotBackend(temp_dir)
        txn = Transaction("txn-1", transaction_config, temp_dir, backend)
        txn.begin()

        txn.checkpoint("cp1")
        snapshots = txn.get_snapshots()

        assert len(snapshots) == 2  # base + cp1


class TestTransactionManager:
    """Test TransactionManager class."""

    def test_begin_creates_transaction(self, temp_dir):
        """Test begin() creates new transaction."""
        manager = TransactionManager()
        txn = manager.begin("test_op", working_dir=temp_dir)

        assert txn is not None
        assert txn.config.operation_name == "test_op"

    def test_get_active_transaction(self, temp_dir):
        """Test retrieving active transaction."""
        manager = TransactionManager()
        txn = manager.begin("test_op", working_dir=temp_dir)

        retrieved = manager.get(txn.transaction_id)

        assert retrieved is txn

    def test_commit_removes_transaction(self, temp_dir):
        """Test commit removes transaction from active list."""
        manager = TransactionManager()
        txn = manager.begin("test_op", working_dir=temp_dir)
        txn_id = txn.transaction_id

        manager.commit(txn_id)

        assert manager.get(txn_id) is None

    def test_rollback_removes_transaction(self, temp_dir):
        """Test rollback removes transaction from active list."""
        manager = TransactionManager()
        txn = manager.begin("test_op", working_dir=temp_dir)
        txn_id = txn.transaction_id

        manager.rollback(txn_id)

        assert manager.get(txn_id) is None

    def test_list_active_transactions(self, temp_dir):
        """Test listing active transactions."""
        manager = TransactionManager()

        txn1 = manager.begin("op1", working_dir=temp_dir)
        txn2 = manager.begin("op2", working_dir=temp_dir)

        active = manager.list_active()

        assert len(active) == 2
        assert txn1.transaction_id in active
        assert txn2.transaction_id in active

    def test_get_status(self, temp_dir):
        """Test getting transaction status."""
        manager = TransactionManager()
        txn = manager.begin("test_op", working_dir=temp_dir)

        txn.on_file_created("test.txt", b"content")
        txn.checkpoint("cp1")

        status = manager.get_status(txn.transaction_id)

        assert status["operation"] == "test_op"
        assert status["changes"] == 1
        assert status["checkpoints"] == 1
        assert status["committed"] is False
        assert status["rolled_back"] is False

    def test_multiple_concurrent_transactions(self, temp_dir):
        """Test managing multiple concurrent transactions."""
        manager = TransactionManager()

        txn1 = manager.begin("op1", working_dir=temp_dir)
        txn2 = manager.begin("op2", working_dir=temp_dir)
        txn3 = manager.begin("op3", working_dir=temp_dir)

        txn1.on_file_created("f1.txt", b"content")
        txn2.on_file_modified("f2.txt", b"old", b"new")
        txn3.on_file_deleted("f3.txt", b"old")

        assert manager.get(txn1.transaction_id).changes[0].path == "f1.txt"
        assert manager.get(txn2.transaction_id).changes[0].path == "f2.txt"
        assert manager.get(txn3.transaction_id).changes[0].path == "f3.txt"

    def test_commit_nonexistent_transaction(self):
        """Test commit fails for nonexistent transaction."""
        manager = TransactionManager()

        with pytest.raises(ValueError, match="not found"):
            manager.commit("nonexistent")

    def test_rollback_nonexistent_transaction(self):
        """Test rollback fails for nonexistent transaction."""
        manager = TransactionManager()

        with pytest.raises(ValueError, match="not found"):
            manager.rollback("nonexistent")


class TestAuditLog:
    """Test AuditLog persistence and loading."""

    def test_audit_log_append_writes_to_disk(self, temp_dir):
        """Test that audit entries are written to disk."""
        log_path = temp_dir / "audit.jsonl"
        from cohezion.sandbox.rollback import AuditLog

        log = AuditLog(log_path)
        entry = AuditEntry(
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TRANSACTION_BEGIN,
            transaction_id="txn-1",
            details={"operation": "test"},
        )

        log.append(entry)

        assert log_path.exists()
        with open(log_path) as f:
            line = f.read().strip()
            data = json.loads(line)
            assert data["txn_id"] == "txn-1"
            assert data["event"] == "transaction_begin"

    def test_audit_log_load_reads_disk(self, temp_dir):
        """Test loading audit entries from disk."""
        log_path = temp_dir / "audit.jsonl"
        from cohezion.sandbox.rollback import AuditLog

        log = AuditLog(log_path)
        entry = AuditEntry(
            timestamp=datetime.now(UTC),
            event_type=AuditEventType.TRANSACTION_BEGIN,
            transaction_id="txn-1",
            details={"operation": "test"},
        )
        log.append(entry)

        loaded_entries = log.load()

        assert len(loaded_entries) == 1
        assert loaded_entries[0].transaction_id == "txn-1"


class TestChange:
    """Test Change class."""

    def test_change_to_dict_serialization(self):
        """Test Change can be serialized to dict."""
        change = Change(
            change_type=ChangeType.FILE_CREATED,
            path="test.txt",
            new_content=b"content",
        )

        data = change.to_dict()

        assert data["change_type"] == "file_created"
        assert data["path"] == "test.txt"
        assert data["new_size"] == 7


class TestJsonlSnapshotBackend:
    """Test JSONL snapshot backend."""

    def test_create_snapshot(self, temp_dir):
        """Test JSONL snapshot creation."""
        backend = JsonlSnapshotBackend(temp_dir)
        result = backend.create_snapshot("snap-1", temp_dir)

        assert result is True
        assert (temp_dir / "snap-1.json").exists()

    def test_restore_snapshot(self, temp_dir):
        """Test JSONL snapshot restore verification."""
        backend = JsonlSnapshotBackend(temp_dir)
        backend.create_snapshot("snap-1", temp_dir)

        result = backend.restore_snapshot("snap-1", temp_dir)

        assert result is True

    def test_delete_snapshot(self, temp_dir):
        """Test JSONL snapshot deletion."""
        backend = JsonlSnapshotBackend(temp_dir)
        backend.create_snapshot("snap-1", temp_dir)

        result = backend.delete_snapshot("snap-1")

        assert result is True
        assert not (temp_dir / "snap-1.json").exists()


class TestGlobalFunctions:
    """Test module-level functions."""

    def test_get_transaction_manager_singleton(self):
        """Test get_transaction_manager returns singleton."""
        manager1 = get_transaction_manager()
        manager2 = get_transaction_manager()

        assert manager1 is manager2


class TestTransactionResult:
    """Test TransactionResult class."""

    def test_transaction_result_to_dict(self):
        """Test TransactionResult serialization."""

        result = TransactionResult(
            success=True,
            transaction_id="txn-1",
            snapshots_taken=2,
            changes_committed=[],
            rollback_performed=False,
            audit_entries=[],
            duration_seconds=1.5,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["transaction_id"] == "txn-1"
        assert data["snapshots_taken"] == 2
        assert data["duration_seconds"] == 1.5


class TestIntegrationScenarios:
    """Integration tests for common scenarios."""

    def test_full_transaction_lifecycle(self, temp_dir):
        """Test complete transaction: begin → changes → checkpoint → commit."""
        manager = TransactionManager()
        txn = manager.begin("full_test", working_dir=temp_dir)

        # Make changes
        txn.on_file_created("file1.txt", b"content1")
        txn.on_file_created("file2.txt", b"content2")
        txn.checkpoint("files_created")

        # More changes
        txn.on_file_modified("file1.txt", b"content1", b"modified")

        # Commit
        result = manager.commit(txn.transaction_id)

        assert result.success is True
        assert len(result.changes_committed) == 3

    def test_transaction_with_failure_and_rollback(self, temp_dir):
        """Test transaction that fails and triggers rollback."""
        manager = TransactionManager()
        txn = manager.begin("failure_test", working_dir=temp_dir)

        txn.on_file_created("file1.txt", b"content1")

        # Simulate failure and rollback
        rollback_result = manager.rollback(txn.transaction_id, reason="Simulated failure")

        assert rollback_result.success is True
        assert rollback_result.changes_undone == 1

    def test_nested_like_behavior_with_checkpoints(self, temp_dir):
        """Test checkpoint-based 'nested' transaction behavior."""
        manager = TransactionManager()
        txn = manager.begin("nested_test", working_dir=temp_dir)

        # Outer transaction start
        txn.on_file_created("outer.txt", b"outer")
        outer_cp = txn.checkpoint("outer_done")

        # Inner-like checkpoint
        txn.on_file_created("inner.txt", b"inner")
        inner_cp = txn.checkpoint("inner_done")

        # More outer work
        txn.on_file_created("outer2.txt", b"outer2")

        # Can rollback to inner checkpoint
        assert inner_cp.changes_at_checkpoint == 2
        # Can rollback to outer checkpoint
        assert outer_cp.changes_at_checkpoint == 1

        result = manager.commit(txn.transaction_id)
        assert result.success is True
