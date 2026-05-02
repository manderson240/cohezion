"""Core type definitions for the graph execution engine.

Defines the data structures for workflow DAGs: nodes, edges, specs, and results.
All types are plain dataclasses with dict serialization for SurrealDB persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.swarm.team_orchestrator import AgentSpec, TaskSpec


class NodeStatus(Enum):
    """Execution status of a workflow node."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeSpec:
    """Specification for a workflow node.

    Maps to a SurrealDB ``workflow_node`` record. The ``node_type`` field
    determines which ``WorkflowNode`` subclass handles execution.
    """

    id: str
    name: str
    node_type: str  # "agent", "tool", "logic_switch", "loop", "subgraph"
    pull_keys: list[str]
    push_keys: list[str]
    attributes: dict[str, Any] = field(default_factory=dict)
    agent_spec: AgentSpec | None = None
    task_spec: TaskSpec | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for SurrealDB storage (excludes runtime objects)."""
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type,
            "pull_keys": self.pull_keys,
            "push_keys": self.push_keys,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeSpec:
        """Deserialize from dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            node_type=data["node_type"],
            pull_keys=data.get("pull_keys", []),
            push_keys=data.get("push_keys", []),
            attributes=data.get("attributes", {}),
        )


@dataclass
class EdgeSpec:
    """Specification for a workflow edge (message channel between nodes).

    Stored via SurrealDB ``RELATE sender->workflow_edge->receiver``.
    Optional ``condition`` enables conditional routing (LogicSwitch patterns).
    """

    id: str
    sender_id: str
    receiver_id: str
    keys: list[str]
    condition: str | None = None
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "keys": self.keys,
            "condition": self.condition,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EdgeSpec:
        return cls(
            id=data["id"],
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            keys=data.get("keys", []),
            condition=data.get("condition"),
            weight=data.get("weight", 1.0),
        )


@dataclass
class WorkflowSpec:
    """Complete workflow specification (DAG).

    A directed acyclic graph of ``NodeSpec`` connected by ``EdgeSpec``.
    Provides graph traversal helpers used by ``WorkflowEngine``.
    """

    id: str
    name: str
    nodes: list[NodeSpec]
    edges: list[EdgeSpec]
    entry_node_id: str
    exit_node_ids: list[str]
    attributes: dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> NodeSpec | None:
        """Look up a node by ID. Returns None if not found."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def adjacency_list(self) -> dict[str, list[str]]:
        """Build forward adjacency list: node_id -> [successor_ids]."""
        adj: dict[str, list[str]] = {n.id: [] for n in self.nodes}
        for edge in self.edges:
            if edge.sender_id in adj:
                adj[edge.sender_id].append(edge.receiver_id)
        return adj

    def predecessors(self, node_id: str) -> list[str]:
        """Return IDs of all nodes that have an edge pointing to ``node_id``."""
        return [e.sender_id for e in self.edges if e.receiver_id == node_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "entry_node_id": self.entry_node_id,
            "exit_node_ids": self.exit_node_ids,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowSpec:
        return cls(
            id=data["id"],
            name=data["name"],
            nodes=[NodeSpec.from_dict(n) for n in data.get("nodes", [])],
            edges=[EdgeSpec.from_dict(e) for e in data.get("edges", [])],
            entry_node_id=data["entry_node_id"],
            exit_node_ids=data.get("exit_node_ids", []),
            attributes=data.get("attributes", {}),
        )


@dataclass
class NodeResult:
    """Result from executing a single workflow node."""

    node_id: str
    status: NodeStatus
    output: dict[str, Any]
    metrics: dict[str, Any]
    duration_ms: float
    error: str | None = None


@dataclass
class WorkflowResult:
    """Result from executing a complete workflow graph."""

    workflow_id: str
    status: str  # "completed", "partial", "failed"
    node_results: dict[str, NodeResult]
    final_output: dict[str, Any]
    total_duration_ms: float
    total_tokens: int
