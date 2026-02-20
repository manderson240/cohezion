"""Tests for session management and context preservation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from cohezion.persistence import SessionManager, SessionSnapshot


@pytest.fixture
def tmp_snapshot_dir(tmp_path):
    """Temporary directory for snapshot storage."""
    return tmp_path / "snapshots"


@pytest.mark.asyncio
async def test_create_snapshot(tmp_snapshot_dir):
    """Test creating a session snapshot."""
    manager = SessionManager(
        session_id="test-session",
        snapshot_dir=tmp_snapshot_dir,
    )

    snapshot = await manager.create_snapshot(
        coherence=0.85,
        active_tasks={"task1": {"status": "in_progress"}},
        skill_context={"current_skill": "analyzer"},
        metrics={"tokens": 1000, "cost": 0.05},
    )

    assert snapshot.session_id == "test-session"
    assert snapshot.coherence == 0.85
    assert "task1" in snapshot.active_tasks

    # Verify file was created
    snapshot_file = tmp_snapshot_dir / "test-session_snapshot.json"
    assert snapshot_file.exists()

    # Verify content
    with open(snapshot_file) as f:
        data = json.load(f)
    assert data["coherence"] == 0.85


@pytest.mark.asyncio
async def test_restore_snapshot(tmp_snapshot_dir):
    """Test restoring a session snapshot."""
    manager = SessionManager(
        session_id="test-session",
        snapshot_dir=tmp_snapshot_dir,
    )

    # Create snapshot
    original = await manager.create_snapshot(
        coherence=0.75,
        active_tasks={"task2": {"status": "pending"}},
        skill_context={"current_skill": "generator"},
        metrics={"tokens": 500},
    )

    # Restore it
    restored = await manager.restore_snapshot("test-session")

    assert restored is not None
    assert restored.session_id == original.session_id
    assert restored.coherence == 0.75
    assert restored.active_tasks == {"task2": {"status": "pending"}}


@pytest.mark.asyncio
async def test_restore_nonexistent_snapshot(tmp_snapshot_dir):
    """Test restoring a snapshot that doesn't exist."""
    manager = SessionManager(
        session_id="test-session",
        snapshot_dir=tmp_snapshot_dir,
    )

    restored = await manager.restore_snapshot("nonexistent")

    assert restored is None


def test_list_snapshots(tmp_snapshot_dir):
    """Test listing available snapshots."""
    # Create snapshot directory and files
    tmp_snapshot_dir.mkdir(parents=True, exist_ok=True)
    (tmp_snapshot_dir / "session1_snapshot.json").write_text("{}")
    (tmp_snapshot_dir / "session2_snapshot.json").write_text("{}")

    manager = SessionManager(
        session_id="test",
        snapshot_dir=tmp_snapshot_dir,
    )

    snapshots = manager.list_snapshots()

    assert len(snapshots) == 2
    assert "session1" in snapshots
    assert "session2" in snapshots


@pytest.mark.asyncio
async def test_cleanup_old_snapshots(tmp_snapshot_dir):
    """Test cleaning up old snapshots."""
    manager = SessionManager(
        session_id="test",
        snapshot_dir=tmp_snapshot_dir,
    )

    # Create 15 snapshots
    for i in range(15):
        await manager.create_snapshot(
            coherence=0.5,
            active_tasks={},
            skill_context={},
            metrics={},
        )
        manager.session_id = f"session-{i}"

    # Cleanup, keeping only 5
    await manager.cleanup_old_snapshots(keep_count=5)

    remaining = manager.list_snapshots()
    assert len(remaining) <= 5


def test_snapshot_serialization():
    """Test snapshot serialization and deserialization."""
    snapshot = SessionSnapshot(
        session_id="test",
        timestamp=datetime.now(),
        coherence=0.9,
        active_tasks={"t1": {"status": "done"}},
        journey_checkpoint={"position": [0.5, 0.3]},
        skill_context={"skill": "analyzer"},
        metrics={"tokens": 200},
    )

    # Serialize
    data = snapshot.to_dict()
    assert data["coherence"] == 0.9

    # Deserialize
    restored = SessionSnapshot.from_dict(data)
    assert restored.session_id == "test"
    assert restored.coherence == 0.9
    assert restored.active_tasks == {"t1": {"status": "done"}}
