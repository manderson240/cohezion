"""Unit tests for LocalAgentBus and TaskGraphWorktreeCoordinator.
================================================================
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cohezion.swarm.coordinate_bus import (
    BusMessage,
    LocalAgentBus,
    MessageType,
    SubtaskSpec,
    SubtaskState,
    TaskGraphWorktreeCoordinator,
)


@pytest.fixture
def temp_bus(tmp_path: Path) -> LocalAgentBus:
    return LocalAgentBus(root_dir=tmp_path)


def test_bus_initialization_and_gitignore(temp_bus: LocalAgentBus, tmp_path: Path):
    assert temp_bus.bus_dir.exists()
    assert temp_bus.inbox_dir.exists()
    assert temp_bus.events_dir.exists()
    assert temp_bus.evidence_dir.exists()

    gitignore = temp_bus.bus_dir / ".gitignore"
    assert gitignore.exists()
    assert "*\n!.gitignore\n" in gitignore.read_text(encoding="utf-8")


def test_publish_and_claim_message(temp_bus: LocalAgentBus):
    msg = BusMessage(
        id="msg-101",
        parent_task_id="task-001",
        subtask_id="sub-1",
        sender="planner",
        recipient="antigravity",
        type=MessageType.IMPLEMENT,
        payload={"instructions": "Implement feature X"},
        dedup_key="hash-101",
    )

    msg_path = temp_bus.publish_message(msg)
    assert msg_path.exists()

    # Claim the message
    claimed = temp_bus.claim_next_message("antigravity", lease_seconds=120.0)
    assert claimed is not None
    assert claimed.id == "msg-101"
    assert claimed.recipient == "antigravity"
    assert claimed.lease_expires_at is not None

    # Processing directory contains claimed message
    proc_path = temp_bus.inbox_dir / "antigravity" / "processing" / "msg-101.json"
    assert proc_path.exists()

    # Complete the message
    temp_bus.complete_message("antigravity", "msg-101")
    assert not proc_path.exists()
    done_path = temp_bus.inbox_dir / "antigravity" / "processed" / "msg-101.json"
    assert done_path.exists()

    # Check Event Journal
    assert temp_bus.journal_file.exists()
    lines = temp_bus.journal_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    event_types = [json.loads(l)["event_type"] for l in lines]
    assert event_types == ["MESSAGE_PUBLISHED", "MESSAGE_CLAIMED", "MESSAGE_COMPLETED"]


def test_corrupted_message_quarantined(temp_bus: LocalAgentBus):
    inbox = temp_bus._agent_inbox("antigravity")
    corrupt_file = inbox / "new" / "corrupt.json"
    corrupt_file.write_text("{invalid json", encoding="utf-8")

    claimed = temp_bus.claim_next_message("antigravity")
    assert claimed is None

    quar_file = inbox / "quarantine" / "corrupt.json"
    assert quar_file.exists()


def test_task_graph_dependency_frontier(temp_bus: LocalAgentBus):
    coordinator = TaskGraphWorktreeCoordinator(temp_bus)

    # Mock _get_head_commit
    coordinator._get_head_commit = MagicMock(return_value="commit-sha-root")

    subtasks = [
        SubtaskSpec(id="st-1", title="Setup core models", assigned_agent="coder"),
        SubtaskSpec(id="st-2", title="Write tests", assigned_agent="tester", dependencies=["st-1"]),
        SubtaskSpec(id="st-3", title="Run benchmarks", assigned_agent="benchmarker", dependencies=["st-2"]),
    ]

    graph = coordinator.create_graph("task-dag-001", "Multi-Agent Refactor", subtasks)

    # Initial state: st-1 has no dependencies -> READY, others -> WAITING
    assert graph.subtasks["st-1"].state == SubtaskState.READY
    assert graph.subtasks["st-2"].state == SubtaskState.WAITING
    assert graph.subtasks["st-3"].state == SubtaskState.WAITING

    # Record st-1 success
    coordinator.record_subtask_success("task-dag-001", "st-1", "commit-sha-st1", {"metrics": "passed"})

    loaded = coordinator.load_graph("task-dag-001")
    assert loaded is not None
    assert loaded.subtasks["st-1"].state == SubtaskState.SUCCEEDED
    assert loaded.subtasks["st-2"].state == SubtaskState.READY
    assert loaded.subtasks["st-3"].state == SubtaskState.WAITING

    # Record st-2 success -> unlocks st-3
    coordinator.record_subtask_success("task-dag-001", "st-2", "commit-sha-st2", {"coverage": 95})

    loaded2 = coordinator.load_graph("task-dag-001")
    assert loaded2.subtasks["st-2"].state == SubtaskState.SUCCEEDED
    assert loaded2.subtasks["st-3"].state == SubtaskState.READY
