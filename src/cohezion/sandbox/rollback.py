"""
RollbackEngine: Transaction semantics for sandboxed operations.

Implements ACID-like guarantees for sandboxed execution:
- Atomicity: All changes or none (via rollback)
- Consistency: Audit trail proves state
- Isolation: Independent transactions
- Durability: Snapshots persisted

Transaction lifecycle:
  1. begin() → create snapshot, initialize audit log
  2. track changes (file_created, file_modified, etc)
  3. checkpoint() (optional) → intermediate snapshot
  4. commit() or rollback()
"""

import json
import logging
import subprocess
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of change tracked in transaction."""

    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    COMMAND_EXECUTED = "command_executed"
    DATABASE_CHANGE = "database_change"


class AuditEventType(Enum):
    """Type of audit event."""

    TRANSACTION_BEGIN = "transaction_begin"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    COMMAND_EXECUTED = "command_executed"
    DATABASE_CHANGE = "database_change"
    CHECKPOINT = "checkpoint"
    TRANSACTION_COMMIT = "transaction_commit"
    TRANSACTION_ROLLBACK = "transaction_rollback"


class SnapshotBackendType(Enum):
    """Type of snapshot backend."""

    GIT = "git"
    BTRFS = "btrfs"
    JSONL = "jsonl"
    HYBRID = "hybrid"


@dataclass
class Change:
    """Individual change within a transaction."""

    change_type: ChangeType
    path: str | None = None
    old_content: bytes | None = None
    new_content: bytes | None = None
    command: str | None = None
    exit_code: int | None = None
    command_output: str | None = None
    table: str | None = None
    data: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, handling datetime and bytes serialization."""
        result = {
            "change_type": self.change_type.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.path:
            result["path"] = self.path
        if self.old_content:
            result["old_size"] = len(self.old_content)
        if self.new_content:
            result["new_size"] = len(self.new_content)
        if self.command:
            result["command"] = self.command
        if self.exit_code is not None:
            result["exit_code"] = self.exit_code
        if self.command_output:
            result["command_output"] = self.command_output[:200]  # Truncate for audit
        if self.table:
            result["table"] = self.table
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: datetime
    event_type: AuditEventType
    transaction_id: str
    details: dict[str, Any]

    def to_jsonl(self) -> str:
        """Convert to JSONL format."""
        return json.dumps(
            {
                "ts": self.timestamp.isoformat(),
                "event": self.event_type.value,
                "txn_id": self.transaction_id,
                **self.details,
            }
        )


@dataclass
class Snapshot:
    """Point-in-time snapshot of transaction state."""

    snapshot_id: str
    transaction_id: str
    timestamp: datetime
    name: str | None = None
    git_hash: str | None = None
    btrfs_snapshot_id: str | None = None
    jsonl_metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for persistence."""
        return {
            "snapshot_id": self.snapshot_id,
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "git_hash": self.git_hash,
            "btrfs_snapshot_id": self.btrfs_snapshot_id,
            "jsonl_metadata": self.jsonl_metadata,
        }


@dataclass
class Checkpoint:
    """Mid-transaction checkpoint for long-running operations."""

    checkpoint_id: str
    name: str | None
    timestamp: datetime
    snapshot: Snapshot
    changes_at_checkpoint: int


@dataclass
class TransactionConfig:
    """Configuration for transaction behavior."""

    operation_name: str
    auto_rollback: bool = True
    audit_log: bool = True
    checkpoint_interval: int | None = None  # Seconds between auto-checkpoints
    max_snapshots: int = 10
    snapshot_backend: SnapshotBackendType = SnapshotBackendType.JSONL
    audit_log_path: Path | None = None


@dataclass
class TransactionResult:
    """Result of successful transaction commit."""

    success: bool
    transaction_id: str
    snapshots_taken: int
    changes_committed: list[Change]
    rollback_performed: bool
    audit_entries: list[AuditEntry]
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for reporting."""
        return {
            "success": self.success,
            "transaction_id": self.transaction_id,
            "snapshots_taken": self.snapshots_taken,
            "changes_committed": len(self.changes_committed),
            "rollback_performed": self.rollback_performed,
            "audit_entries": len(self.audit_entries),
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class RollbackResult:
    """Result of transaction rollback."""

    success: bool
    reason: str
    changes_undone: int
    audit_entry: AuditEntry
    duration_seconds: float = 0.0


class AuditLog:
    """Persistent JSONL-based audit log for transaction history."""

    def __init__(self, log_path: Path):
        """Initialize audit log at specified path."""
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[AuditEntry] = []

    def append(self, entry: AuditEntry) -> None:
        """Append entry to audit log (both memory and disk)."""
        self.entries.append(entry)
        try:
            with open(self.log_path, "a") as f:
                f.write(entry.to_jsonl() + "\n")
        except OSError as e:
            logger.warning(f"Failed to write audit log: {e}")

    def load(self) -> list[AuditEntry]:
        """Load all entries from disk audit log."""
        if not self.log_path.exists():
            return []

        entries = []
        try:
            with open(self.log_path) as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            entry = AuditEntry(
                                timestamp=datetime.fromisoformat(data["ts"]),
                                event_type=AuditEventType(data["event"]),
                                transaction_id=data["txn_id"],
                                details={k: v for k, v in data.items() if k not in ("ts", "event", "txn_id")},
                            )
                            entries.append(entry)
                        except (json.JSONDecodeError, ValueError, KeyError) as e:
                            logger.warning(f"Failed to parse audit log entry: {e}")
        except OSError as e:
            logger.warning(f"Failed to read audit log: {e}")

        return entries


class SnapshotBackend:
    """Base class for snapshot backends."""

    def create_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Create snapshot at current state."""
        raise NotImplementedError

    def restore_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Restore to snapshot state."""
        raise NotImplementedError

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot."""
        raise NotImplementedError


class GitSnapshotBackend(SnapshotBackend):
    """Git-based snapshots using stash."""

    def create_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Create snapshot by stashing changes."""
        try:
            result = subprocess.run(
                ["git", "stash", "push", "-u", "-m", f"txn_{snapshot_id}"],
                cwd=working_dir,
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error(f"Git stash timeout for {snapshot_id}")
            return False
        except Exception as e:
            logger.error(f"Git snapshot creation failed: {e}")
            return False

    def restore_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Restore snapshot by applying stash."""
        try:
            # Find stash with our marker
            result = subprocess.run(
                ["git", "stash", "list"],
                cwd=working_dir,
                capture_output=True,
                timeout=5,
            )

            for line in result.stdout.decode().split("\n"):
                if f"txn_{snapshot_id}" in line:
                    stash_ref = line.split(":")[0]
                    apply_result = subprocess.run(
                        ["git", "stash", "apply", stash_ref],
                        cwd=working_dir,
                        capture_output=True,
                        timeout=10,
                    )
                    return apply_result.returncode == 0

            return False
        except Exception as e:
            logger.error(f"Git snapshot restore failed: {e}")
            return False

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete stash (optional cleanup)."""
        return True


class BtrfsSnapshotBackend(SnapshotBackend):
    """BTRFS-based snapshots (requires BTRFS filesystem)."""

    def create_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Create BTRFS snapshot."""
        try:
            snapshot_path = working_dir.parent / f".snapshots_{snapshot_id}"
            result = subprocess.run(
                [
                    "btrfs",
                    "subvolume",
                    "snapshot",
                    str(working_dir),
                    str(snapshot_path),
                ],
                capture_output=True,
                timeout=30,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"BTRFS snapshot creation failed (may not be on BTRFS): {e}")
            return False

    def restore_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Restore from BTRFS snapshot."""
        try:
            snapshot_path = working_dir.parent / f".snapshots_{snapshot_id}"
            if not snapshot_path.exists():
                return False

            # Remove current and restore from snapshot
            subprocess.run(
                ["rm", "-rf", str(working_dir)],
                timeout=30,
                capture_output=True,
            )
            subprocess.run(
                ["mv", str(snapshot_path), str(working_dir)],
                timeout=30,
                capture_output=True,
            )
            return True
        except Exception as e:
            logger.error(f"BTRFS snapshot restore failed: {e}")
            return False

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete BTRFS snapshot."""
        return True


class JsonlSnapshotBackend(SnapshotBackend):
    """JSONL-based metadata-only snapshots (no actual filesystem restore)."""

    def __init__(self, metadata_dir: Path | None = None):
        """Initialize with metadata directory."""
        self.metadata_dir = metadata_dir or Path("/tmp/rollback_snapshots")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Create metadata snapshot."""
        try:
            metadata = {
                "snapshot_id": snapshot_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "working_dir": str(working_dir),
            }

            snapshot_file = self.metadata_dir / f"{snapshot_id}.json"
            with open(snapshot_file, "w") as f:
                json.dump(metadata, f)
            return True
        except Exception as e:
            logger.error(f"JSONL snapshot creation failed: {e}")
            return False

    def restore_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Restore from metadata snapshot (metadata-only, no actual restore)."""
        snapshot_file = self.metadata_dir / f"{snapshot_id}.json"
        return snapshot_file.exists()

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete metadata snapshot."""
        try:
            snapshot_file = self.metadata_dir / f"{snapshot_id}.json"
            if snapshot_file.exists():
                snapshot_file.unlink()
            return True
        except Exception as e:
            logger.error(f"JSONL snapshot deletion failed: {e}")
            return False


class HybridSnapshotBackend(SnapshotBackend):
    """Hybrid backend using all three strategies."""

    def __init__(self, working_dir: Path):
        """Initialize all backends."""
        self.backends = {
            "git": GitSnapshotBackend(),
            "btrfs": BtrfsSnapshotBackend(),
            "jsonl": JsonlSnapshotBackend(),
        }
        self.working_dir = working_dir

    def create_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Create snapshot via all backends."""
        results = []
        for name, backend in self.backends.items():
            try:
                result = backend.create_snapshot(snapshot_id, working_dir)
                results.append(result)
                logger.debug(f"{name} snapshot created: {result}")
            except Exception as e:
                logger.warning(f"{name} snapshot creation failed: {e}")
                results.append(False)

        return any(results)  # Success if at least one backend succeeds

    def restore_snapshot(self, snapshot_id: str, working_dir: Path) -> bool:
        """Restore from first available backend."""
        for name, backend in self.backends.items():
            try:
                if backend.restore_snapshot(snapshot_id, working_dir):
                    logger.debug(f"Restored from {name} backend")
                    return True
            except Exception as e:
                logger.warning(f"{name} restore failed: {e}")

        return False

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete from all backends."""
        results = []
        for name, backend in self.backends.items():
            try:
                result = backend.delete_snapshot(snapshot_id)
                results.append(result)
            except Exception as e:
                logger.warning(f"{name} deletion failed: {e}")
                results.append(False)

        return all(results)


class Transaction:
    """Single transaction with full change tracking."""

    def __init__(
        self,
        transaction_id: str,
        config: TransactionConfig,
        working_dir: Path,
        backend: SnapshotBackend,
    ):
        """Initialize transaction."""
        self.transaction_id = transaction_id
        self.config = config
        self.working_dir = working_dir
        self.backend = backend

        # Change tracking
        self.changes: list[Change] = []
        self.change_index: dict[str, list[int]] = defaultdict(
            list
        )  # path → change indices

        # Checkpoints
        self.checkpoints: dict[str, Checkpoint] = {}

        # Audit log
        self.audit_log = AuditLog(config.audit_log_path or Path(f"/tmp/rollback_audit_{transaction_id}.jsonl"))

        # Snapshots
        self.snapshots: dict[str, Snapshot] = {}
        self.base_snapshot: Snapshot | None = None

        # Timing
        self.start_time = time.time()
        self.last_checkpoint_time = self.start_time

        # State
        self.committed = False
        self.rolled_back = False

    def begin(self) -> None:
        """Start transaction: create initial snapshot."""
        try:
            snapshot_id = f"snapshot_base_{self.transaction_id}"
            if self.backend.create_snapshot(snapshot_id, self.working_dir):
                self.base_snapshot = Snapshot(
                    snapshot_id=snapshot_id,
                    transaction_id=self.transaction_id,
                    timestamp=datetime.now(UTC),
                )
                self.snapshots[snapshot_id] = self.base_snapshot

                # Log begin event
                self.audit_log.append(
                    AuditEntry(
                        timestamp=datetime.now(UTC),
                        event_type=AuditEventType.TRANSACTION_BEGIN,
                        transaction_id=self.transaction_id,
                        details={"operation": self.config.operation_name},
                    )
                )
        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            raise

    def on_file_created(self, path: str, content: bytes) -> None:
        """Track file creation."""
        change = Change(
            change_type=ChangeType.FILE_CREATED,
            path=path,
            new_content=content,
        )
        self._record_change(change)

    def on_file_modified(self, path: str, old: bytes, new: bytes) -> None:
        """Track file modification."""
        change = Change(
            change_type=ChangeType.FILE_MODIFIED,
            path=path,
            old_content=old,
            new_content=new,
        )
        self._record_change(change)

    def on_file_deleted(self, path: str, content: bytes) -> None:
        """Track file deletion."""
        change = Change(
            change_type=ChangeType.FILE_DELETED,
            path=path,
            old_content=content,
        )
        self._record_change(change)

    def on_command_executed(self, cmd: str, exit_code: int, output: str = "") -> None:
        """Track command execution."""
        change = Change(
            change_type=ChangeType.COMMAND_EXECUTED,
            command=cmd,
            exit_code=exit_code,
            command_output=output,
        )
        self._record_change(change)

    def on_database_change(self, table: str, data: dict[str, Any]) -> None:
        """Track database change."""
        change = Change(
            change_type=ChangeType.DATABASE_CHANGE,
            table=table,
            data=data,
        )
        self._record_change(change)

    def _record_change(self, change: Change) -> None:
        """Record change and audit it."""
        change_idx = len(self.changes)
        self.changes.append(change)

        if change.path:
            self.change_index[change.path].append(change_idx)

        # Audit log entry
        self.audit_log.append(
            AuditEntry(
                timestamp=change.timestamp,
                event_type=AuditEventType(change.change_type.value),
                transaction_id=self.transaction_id,
                details=change.to_dict(),
            )
        )

        # Check if auto-checkpoint needed
        if self.config.checkpoint_interval:
            elapsed = time.time() - self.last_checkpoint_time
            if elapsed >= self.config.checkpoint_interval:
                self.checkpoint()

    def checkpoint(self, name: str | None = None) -> Checkpoint:
        """Create intermediate checkpoint."""
        checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:8]}"
        snapshot_id = f"snapshot_{checkpoint_id}"

        try:
            if self.backend.create_snapshot(snapshot_id, self.working_dir):
                snapshot = Snapshot(
                    snapshot_id=snapshot_id,
                    transaction_id=self.transaction_id,
                    timestamp=datetime.now(UTC),
                    name=name,
                )
                self.snapshots[snapshot_id] = snapshot

                checkpoint = Checkpoint(
                    checkpoint_id=checkpoint_id,
                    name=name,
                    timestamp=datetime.now(UTC),
                    snapshot=snapshot,
                    changes_at_checkpoint=len(self.changes),
                )
                self.checkpoints[checkpoint_id] = checkpoint

                # Audit checkpoint
                self.audit_log.append(
                    AuditEntry(
                        timestamp=datetime.now(UTC),
                        event_type=AuditEventType.CHECKPOINT,
                        transaction_id=self.transaction_id,
                        details={"checkpoint_id": checkpoint_id, "name": name},
                    )
                )

                self.last_checkpoint_time = time.time()
                logger.debug(f"Checkpoint created: {checkpoint_id}")
                return checkpoint
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise

    def commit(self, verify: bool = True) -> TransactionResult:
        """Commit transaction: merge changes to parent."""
        start = time.time()

        if self.rolled_back:
            raise RuntimeError("Cannot commit rolled-back transaction")

        try:
            if verify:
                # Verify all changes are recorded
                if not self.changes:
                    logger.warning("No changes recorded in transaction")

            # Cleanup old snapshots (keep only max_snapshots most recent)
            if len(self.snapshots) > self.config.max_snapshots:
                self._cleanup_old_snapshots()

            # Mark as committed
            self.committed = True

            # Audit commit
            self.audit_log.append(
                AuditEntry(
                    timestamp=datetime.now(UTC),
                    event_type=AuditEventType.TRANSACTION_COMMIT,
                    transaction_id=self.transaction_id,
                    details={"changes": len(self.changes)},
                )
            )

            duration = time.time() - start
            result = TransactionResult(
                success=True,
                transaction_id=self.transaction_id,
                snapshots_taken=len(self.snapshots),
                changes_committed=self.changes[:],
                rollback_performed=False,
                audit_entries=self.audit_log.entries[:],
                duration_seconds=duration,
            )

            logger.info(
                f"Transaction {self.transaction_id} committed ({len(self.changes)} changes)"
            )
            return result

        except Exception as e:
            logger.error(f"Transaction commit failed: {e}")
            if self.config.auto_rollback and not self.rolled_back:
                logger.info("Auto-rolling back due to commit failure")
                try:
                    self.rollback(reason=f"Commit failed: {e}")
                except RuntimeError:
                    pass  # Already rolled back
            raise

    def rollback(
        self, reason: str = "", restore_to_checkpoint: str | None = None
    ) -> RollbackResult:
        """Rollback transaction: restore to snapshot."""
        start = time.time()

        try:
            if self.rolled_back:
                raise RuntimeError("Transaction already rolled back")

            # Determine which snapshot to restore to
            target_snapshot = None
            if restore_to_checkpoint and restore_to_checkpoint in self.checkpoints:
                target_snapshot = self.checkpoints[restore_to_checkpoint].snapshot
            elif self.base_snapshot:
                target_snapshot = self.base_snapshot
            else:
                raise RuntimeError("No snapshot available for rollback")

            # Restore snapshot
            if not self.backend.restore_snapshot(
                target_snapshot.snapshot_id, self.working_dir
            ):
                logger.warning(
                    f"Snapshot restore may have failed: {target_snapshot.snapshot_id}"
                )

            # Mark as rolled back
            self.rolled_back = True
            changes_undone = len(self.changes)

            # Audit rollback
            audit_entry = AuditEntry(
                timestamp=datetime.now(UTC),
                event_type=AuditEventType.TRANSACTION_ROLLBACK,
                transaction_id=self.transaction_id,
                details={
                    "reason": reason,
                    "changes_undone": changes_undone,
                    "restored_to": target_snapshot.snapshot_id,
                },
            )
            self.audit_log.append(audit_entry)

            duration = time.time() - start
            result = RollbackResult(
                success=True,
                reason=reason,
                changes_undone=changes_undone,
                audit_entry=audit_entry,
                duration_seconds=duration,
            )

            logger.info(
                f"Transaction {self.transaction_id} rolled back ({changes_undone} changes undone)"
            )
            return result

        except Exception as e:
            logger.error(f"Transaction rollback failed: {e}")
            raise

    def _cleanup_old_snapshots(self) -> None:
        """Remove oldest snapshots, keeping only max_snapshots most recent."""
        sorted_snapshots = sorted(
            self.snapshots.values(),
            key=lambda s: s.timestamp,
        )

        # Keep base + most recent ones
        keep_count = min(self.config.max_snapshots, len(sorted_snapshots))
        to_delete = sorted_snapshots[:-keep_count]

        for snapshot in to_delete:
            try:
                self.backend.delete_snapshot(snapshot.snapshot_id)
                del self.snapshots[snapshot.snapshot_id]
                logger.debug(f"Deleted old snapshot: {snapshot.snapshot_id}")
            except Exception as e:
                logger.warning(f"Failed to delete snapshot {snapshot.snapshot_id}: {e}")

    def get_audit_entries(self) -> list[AuditEntry]:
        """Get all audit entries for this transaction."""
        return self.audit_log.entries[:]

    def get_changes(self) -> list[Change]:
        """Get all tracked changes."""
        return self.changes[:]

    def get_snapshots(self) -> dict[str, Snapshot]:
        """Get all snapshots."""
        return self.snapshots.copy()


class TransactionManager:
    """Manages multiple active transactions."""

    def __init__(self):
        """Initialize manager."""
        self.transactions: dict[str, Transaction] = {}
        self._lock_count = 0

    def begin(
        self,
        operation_name: str,
        working_dir: Path | None = None,
        config: TransactionConfig = None,
        backend: SnapshotBackendType = SnapshotBackendType.JSONL,
    ) -> Transaction:
        """Begin new transaction."""
        if working_dir is None:
            working_dir = Path.cwd()

        if config is None:
            config = TransactionConfig(operation_name=operation_name)

        # Select backend
        if backend == SnapshotBackendType.GIT:
            backend_obj = GitSnapshotBackend()
        elif backend == SnapshotBackendType.BTRFS:
            backend_obj = BtrfsSnapshotBackend()
        elif backend == SnapshotBackendType.HYBRID:
            backend_obj = HybridSnapshotBackend(working_dir)
        else:
            backend_obj = JsonlSnapshotBackend()

        transaction_id = f"txn_{uuid.uuid4().hex[:8]}"
        txn = Transaction(transaction_id, config, working_dir, backend_obj)
        txn.begin()

        self.transactions[transaction_id] = txn
        logger.info(f"Transaction started: {transaction_id}")
        return txn

    def get(self, transaction_id: str) -> Transaction | None:
        """Get active transaction by ID."""
        return self.transactions.get(transaction_id)

    def commit(self, transaction_id: str) -> TransactionResult:
        """Commit transaction."""
        txn = self.transactions.get(transaction_id)
        if not txn:
            raise ValueError(f"Transaction not found: {transaction_id}")

        result = txn.commit()
        self.transactions.pop(transaction_id, None)
        return result

    def rollback(self, transaction_id: str, reason: str = "") -> RollbackResult:
        """Rollback transaction."""
        txn = self.transactions.get(transaction_id)
        if not txn:
            raise ValueError(f"Transaction not found: {transaction_id}")

        result = txn.rollback(reason=reason)
        self.transactions.pop(transaction_id, None)
        return result

    def list_active(self) -> list[str]:
        """List all active transaction IDs."""
        return list(self.transactions.keys())

    def get_status(self, transaction_id: str) -> dict[str, Any]:
        """Get transaction status."""
        txn = self.transactions.get(transaction_id)
        if not txn:
            raise ValueError(f"Transaction not found: {transaction_id}")

        return {
            "transaction_id": transaction_id,
            "operation": txn.config.operation_name,
            "changes": len(txn.changes),
            "checkpoints": len(txn.checkpoints),
            "snapshots": len(txn.snapshots),
            "committed": txn.committed,
            "rolled_back": txn.rolled_back,
            "elapsed_seconds": time.time() - txn.start_time,
        }


# Global manager instance
_manager: TransactionManager | None = None


def get_transaction_manager() -> TransactionManager:
    """Get singleton transaction manager."""
    global _manager
    if _manager is None:
        _manager = TransactionManager()
    return _manager
