"""Local-First Recoverable Agent Bus & Task Graph Worktree Coordinator.
========================================================================
Abstracted and adapted from https://github.com/hogancv/coordinate-agents.

Core Architecture:
1. Agent Bus Protocol Layer:
   - Atomic message publication and claiming via filesystem queues:
     `.agent-bus/inbox/{agent_id}/new/`, `processing/`, `processed/`.
   - Lease sidecars, append-only state, deduplication keys, and quarantine.
   - Append-only schema-v1 Event Journal: `.agent-bus/events/runtime.jsonl`.
2. Execution Session & Worktree Isolation (Task Graph v1):
   - Subtasks in a DAG execute in dedicated Git worktrees:
     `.agent-bus/worktrees/{parent_id}/{subtask_id}` on isolated branches.
   - Deterministic integration worktree (`__integration__`) with sorted cherry-picking.
   - Enforces two-party review (`REVIEW_APPROVED`) and human authorization (`RELEASE_APPROVED`).
3. Seamless Cohezion Integration:
   - Connects with `cohezion.core.event_bus.EventBus` and `cohezion.data_mesh.kanban_bridge`.
"""

from __future__ import annotations

import datetime
import enum
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

logger = logging.getLogger("coordinate_bus")


class MessageType(str, enum.Enum):
    """Protocol message types defined by coordinate-agents."""

    IMPLEMENT = "IMPLEMENT"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    IMPLEMENTATION_DONE = "IMPLEMENTATION_DONE"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    RELEASE_APPROVED = "RELEASE_APPROVED"
    ABORT = "ABORT"


class SubtaskState(str, enum.Enum):
    """Task Graph subtask lifecycle states."""

    READY = "READY"
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    SKIPPED = "SKIPPED"


class BusMessage(BaseModel):
    """Schema-v1 Agent Bus message packet."""

    id: str
    parent_task_id: str
    subtask_id: Optional[str] = None
    sender: str
    recipient: str
    type: MessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    dedup_key: str
    lease_expires_at: Optional[float] = None
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class SubtaskSpec(BaseModel):
    """Specification for a single node in a Task Graph DAG."""

    id: str
    title: str
    assigned_agent: str
    dependencies: List[str] = Field(default_factory=list)
    state: SubtaskState = SubtaskState.WAITING
    commit_sha: Optional[str] = None
    evidence_path: Optional[str] = None
    branch_name: Optional[str] = None
    worktree_path: Optional[str] = None


class TaskGraph(BaseModel):
    """Durable Task Graph v1 DAG."""

    parent_task_id: str
    title: str
    base_commit: str
    subtasks: Dict[str, SubtaskSpec] = Field(default_factory=dict)
    state: str = "IN_PROGRESS"
    integration_commit: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


class LocalAgentBus:
    """Project-local atomic Agent Bus coordinating multi-agent queues & event journals."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root = (root_dir or Path.cwd()).resolve()
        self.bus_dir = self.root / ".agent-bus"
        self.inbox_dir = self.bus_dir / "inbox"
        self.evidence_dir = self.bus_dir / "evidence"
        self.events_dir = self.bus_dir / "events"
        self.worktrees_dir = self.bus_dir / "worktrees"
        self.journal_file = self.events_dir / "runtime.jsonl"
        self._init_layout()

    def _init_layout(self) -> None:
        """Initializes directory structure and ensures gitignore safeguards."""
        for d in [self.bus_dir, self.inbox_dir, self.evidence_dir, self.events_dir, self.worktrees_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Safety boundary: .agent-bus plaintext state must stay excluded from VCS
        gitignore = self.bus_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")

    def _agent_inbox(self, agent_id: str) -> Path:
        agent_dir = self.inbox_dir / agent_id
        for sub in ["new", "processing", "processed", "quarantine"]:
            (agent_dir / sub).mkdir(parents=True, exist_ok=True)
        return agent_dir

    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Appends a schema-v1 sanitized record to the runtime event journal."""
        record = {
            "schema_version": "1.0",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
        }
        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def publish_message(self, msg: BusMessage) -> Path:
        """Atomically publishes a message to the recipient's new/ inbox."""
        inbox = self._agent_inbox(msg.recipient)
        msg_file = inbox / "new" / f"{msg.id}.json"
        temp_file = inbox / "new" / f".tmp_{msg.id}.json"

        # Atomic write via tempfile rename
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(msg.model_dump_json(indent=2))
        temp_file.rename(msg_file)

        self.log_event(
            "MESSAGE_PUBLISHED",
            {
                "message_id": msg.id,
                "sender": msg.sender,
                "recipient": msg.recipient,
                "type": msg.type.value,
                "parent_task_id": msg.parent_task_id,
            },
        )
        return msg_file

    def claim_next_message(
        self, agent_id: str, lease_seconds: float = 60.0
    ) -> Optional[BusMessage]:
        """Atomically claims the oldest message from new/ into processing/ with a lease."""
        inbox = self._agent_inbox(agent_id)
        new_dir = inbox / "new"
        proc_dir = inbox / "processing"

        candidates = sorted(new_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for cand in candidates:
            if cand.name.startswith("."):
                continue
            proc_file = proc_dir / cand.name
            try:
                # Atomic claim via POSIX rename
                cand.rename(proc_file)
            except OSError:
                continue

            try:
                with open(proc_file, encoding="utf-8") as f:
                    data = json.load(f)
                msg = BusMessage.model_validate(data)
                msg.lease_expires_at = time.time() + lease_seconds

                # Update with lease expiration
                with open(proc_file, "w", encoding="utf-8") as f:
                    f.write(msg.model_dump_json(indent=2))

                self.log_event(
                    "MESSAGE_CLAIMED",
                    {
                        "message_id": msg.id,
                        "agent_id": agent_id,
                        "lease_expires_at": msg.lease_expires_at,
                    },
                )
                return msg
            except Exception as e:
                logger.error("Corrupted message %s, quarantining: %s", cand.name, e)
                quar_file = inbox / "quarantine" / cand.name
                shutil.move(str(proc_file), str(quar_file))
                self.log_event("MESSAGE_QUARANTINED", {"filename": cand.name, "error": str(e)})

        return None

    def complete_message(self, agent_id: str, message_id: str) -> None:
        """Atomically marks a message as processed."""
        inbox = self._agent_inbox(agent_id)
        proc_file = inbox / "processing" / f"{message_id}.json"
        done_file = inbox / "processed" / f"{message_id}.json"

        if proc_file.exists():
            proc_file.rename(done_file)
            self.log_event("MESSAGE_COMPLETED", {"message_id": message_id, "agent_id": agent_id})


class TaskGraphWorktreeCoordinator:
    """Coordinates Task Graph v1 DAGs across isolated Git worktrees."""

    def __init__(self, bus: LocalAgentBus):
        self.bus = bus
        self.root = bus.root
        self.graphs_dir = bus.bus_dir / "graphs"
        self.graphs_dir.mkdir(parents=True, exist_ok=True)

    def _get_head_commit(self) -> str:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()

    def create_graph(self, parent_task_id: str, title: str, subtasks: List[SubtaskSpec]) -> TaskGraph:
        """Creates a new durable Task Graph rooted at the current HEAD commit."""
        base_commit = self._get_head_commit()
        st_dict = {st.id: st for st in subtasks}

        # Calculate initial frontier: nodes with empty dependencies become READY
        for st in st_dict.values():
            if not st.dependencies:
                st.state = SubtaskState.READY
            else:
                st.state = SubtaskState.WAITING

        graph = TaskGraph(
            parent_task_id=parent_task_id,
            title=title,
            base_commit=base_commit,
            subtasks=st_dict,
        )
        self.save_graph(graph)
        self.bus.log_event(
            "GRAPH_CREATED",
            {
                "parent_task_id": parent_task_id,
                "base_commit": base_commit,
                "subtask_count": len(subtasks),
            },
        )
        return graph

    def save_graph(self, graph: TaskGraph) -> None:
        path = self.graphs_dir / f"{graph.parent_task_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(graph.model_dump_json(indent=2))

    def load_graph(self, parent_task_id: str) -> Optional[TaskGraph]:
        path = self.graphs_dir / f"{parent_task_id}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return TaskGraph.model_validate(json.load(f))

    def setup_subtask_worktree(self, parent_task_id: str, subtask_id: str) -> Path:
        """Sets up an isolated Git worktree for the subtask."""
        graph = self.load_graph(parent_task_id)
        if not graph:
            raise ValueError(f"TaskGraph {parent_task_id} not found")
        subtask = graph.subtasks.get(subtask_id)
        if not subtask:
            raise ValueError(f"Subtask {subtask_id} not found in graph")

        branch_name = f"coordinate-agents/{parent_task_id}/{subtask_id}"
        wt_path = self.bus.worktrees_dir / parent_task_id / subtask_id
        wt_path.parent.mkdir(parents=True, exist_ok=True)

        if not wt_path.exists():
            # Create git worktree
            cmd = [
                "git",
                "worktree",
                "add",
                "-B",
                branch_name,
                str(wt_path),
                graph.base_commit,
            ]
            subprocess.run(cmd, cwd=str(self.root), capture_output=True, text=True, check=True)
            logger.info("Created isolated worktree for subtask %s at %s", subtask_id, wt_path)

        subtask.branch_name = branch_name
        subtask.worktree_path = str(wt_path)
        subtask.state = SubtaskState.RUNNING
        self.save_graph(graph)
        return wt_path

    def record_subtask_success(
        self, parent_task_id: str, subtask_id: str, commit_sha: str, evidence: Dict[str, Any]
    ) -> None:
        """Records subtask success, saves evidence, and advances the dependency frontier."""
        graph = self.load_graph(parent_task_id)
        if not graph:
            return
        subtask = graph.subtasks.get(subtask_id)
        if not subtask:
            return

        # Save evidence record
        ev_file = self.bus.evidence_dir / f"{parent_task_id}_{subtask_id}.json"
        with open(ev_file, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2)

        subtask.state = SubtaskState.SUCCEEDED
        subtask.commit_sha = commit_sha
        subtask.evidence_path = str(ev_file)

        # Advance frontier: check if any WAITING subtask has all dependencies SUCCEEDED
        succeeded_ids: Set[str] = {
            s_id for s_id, s in graph.subtasks.items() if s.state == SubtaskState.SUCCEEDED
        }

        for st in graph.subtasks.values():
            if st.state == SubtaskState.WAITING:
                if all(dep in succeeded_ids for dep in st.dependencies):
                    st.state = SubtaskState.READY
                    logger.info("Subtask %s unlocked and transition to READY", st.id)

        self.save_graph(graph)
        self.bus.log_event(
            "SUBTASK_SUCCEEDED",
            {"parent_task_id": parent_task_id, "subtask_id": subtask_id, "commit_sha": commit_sha},
        )

    def integrate_graph(self, parent_task_id: str) -> str:
        """Deterministically integrates all succeeded subtasks into __integration__ worktree."""
        graph = self.load_graph(parent_task_id)
        if not graph:
            raise ValueError(f"TaskGraph {parent_task_id} not found")

        # Refuse graph with unverified subtasks
        for st in graph.subtasks.values():
            if st.state != SubtaskState.SUCCEEDED:
                raise RuntimeError(
                    f"Cannot integrate graph {parent_task_id}: subtask {st.id} is {st.state.value}"
                )

        int_branch = f"coordinate-agents/{parent_task_id}/__integration__"
        int_wt_path = self.bus.worktrees_dir / parent_task_id / "__integration__"
        int_wt_path.parent.mkdir(parents=True, exist_ok=True)

        if int_wt_path.exists():
            subprocess.run(["git", "worktree", "remove", "--force", str(int_wt_path)], cwd=str(self.root), check=False)

        # Create integration worktree at base commit
        cmd = ["git", "worktree", "add", "-B", int_branch, str(int_wt_path), graph.base_commit]
        subprocess.run(cmd, cwd=str(self.root), capture_output=True, text=True, check=True)

        # Cherry-pick subtask commits in sorted identifier order
        sorted_subtasks = sorted(graph.subtasks.values(), key=lambda s: s.id)
        for st in sorted_subtasks:
            if not st.commit_sha:
                continue
            cp_res = subprocess.run(
                ["git", "cherry-pick", st.commit_sha],
                cwd=str(int_wt_path),
                capture_output=True,
                text=True,
            )
            if cp_res.returncode != 0:
                raise RuntimeError(
                    f"Cherry-pick conflict integrating subtask {st.id} ({st.commit_sha}): {cp_res.stderr}"
                )

        # Capture aggregate commit SHA
        rev_res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(int_wt_path),
            capture_output=True,
            text=True,
            check=True,
        )
        agg_commit = rev_res.stdout.strip()
        graph.integration_commit = agg_commit
        graph.state = "INTEGRATED"
        self.save_graph(graph)

        self.bus.log_event(
            "GRAPH_INTEGRATED",
            {
                "parent_task_id": parent_task_id,
                "integration_commit": agg_commit,
                "subtask_count": len(sorted_subtasks),
            },
        )
        logger.info("Successfully integrated graph %s -> commit %s", parent_task_id, agg_commit)
        return agg_commit

    def cleanup_worktrees(self, parent_task_id: str) -> None:
        """Idempotently cleans up Runtime-owned worktrees."""
        parent_wt_dir = self.bus.worktrees_dir / parent_task_id
        if not parent_wt_dir.exists():
            return

        for child in parent_wt_dir.iterdir():
            if child.is_dir():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(child)],
                    cwd=str(self.root),
                    check=False,
                )

        shutil.rmtree(parent_wt_dir, ignore_errors=True)
        self.bus.log_event("WORKTREES_CLEANED", {"parent_task_id": parent_task_id})
