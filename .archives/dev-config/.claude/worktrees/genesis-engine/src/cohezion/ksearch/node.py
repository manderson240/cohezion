"""K-Search node module for tree node management."""

from __future__ import annotations

from enum import Enum
from typing import Any


class NodeStatus(Enum):
    """Status values for search tree nodes."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRUNED = "PRUNED"


class Node:
    """Represents a node in the kernel optimization search tree.

    Attributes:
        id: Unique node identifier
        name: Human-readable name
        description: Detailed description
        status: Current node status
        priority: Priority score (0.0-1.0)
        attempts: Number of optimization attempts
        stagnation_count: Consecutive failed attempts
        parent_id: Parent node ID (None for root)
        config: Kernel configuration dict
        expected_gain: Expected performance gain
        risk: Risk level (low/medium/high)
        notes: Additional notes
        children: Child nodes
    """

    def __init__(
        self,
        id: str = "",
        name: str = "",
        description: str = "",
        status: str | NodeStatus = NodeStatus.OPEN,
        priority: float = 0.0,
        attempts: int = 0,
        stagnation_count: int = 0,
        parent_id: str | None = None,
        config: dict[str, Any] | None = None,
        expected_gain: str = "",
        risk: str = "medium",
        notes: str = "",
        children: list[Node] | None = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.status = status if isinstance(status, NodeStatus) else NodeStatus(status)
        self.priority = priority
        self.attempts = attempts
        self.stagnation_count = stagnation_count
        self.parent_id = parent_id
        self.config = config or {}
        self.expected_gain = expected_gain
        self.risk = risk
        self.notes = notes
        self.children = children or []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        """Create a Node from a dictionary."""
        children_data = data.get("children", [])
        children = [Node.from_dict(c) for c in children_data if isinstance(c, dict)]

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=data.get("status", NodeStatus.OPEN),
            priority=data.get("priority", 0.0),
            attempts=data.get("attempts", 0),
            stagnation_count=data.get("stagnation_count", 0),
            parent_id=data.get("parent_id"),
            config=data.get("config", {}),
            expected_gain=data.get("expected_gain", ""),
            risk=data.get("risk", "medium"),
            notes=data.get("notes", ""),
            children=children,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the Node to a dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "attempts": self.attempts,
            "stagnation_count": self.stagnation_count,
            "config": self.config,
        }
        if self.parent_id:
            result["parent_id"] = self.parent_id
        if self.expected_gain:
            result["expected_gain"] = self.expected_gain
        if self.risk:
            result["risk"] = self.risk
        if self.notes:
            result["notes"] = self.notes
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result

    def count_subtree(self) -> int:
        """Count total nodes in this subtree."""
        return 1 + sum(c.count_subtree() for c in self.children)

    def count_by_status(self, status: str) -> int:
        """Count nodes with specific status in this subtree."""
        count = 1 if self.status.value == status else 0
        return count + sum(c.count_by_status(status) for c in self.children)

    def find_in_subtree(self, node_id: str) -> Node | None:
        """Find a node by ID in this subtree."""
        if self.id == node_id:
            return self
        for child in self.children:
            result = child.find_in_subtree(node_id)
            if result:
                return result
        return None

    def get_open_in_subtree(self) -> list[Node]:
        """Get all OPEN nodes in this subtree, sorted by priority."""
        result = []
        if self.status == NodeStatus.OPEN:
            result.append(self)
        for child in self.children:
            result.extend(child.get_open_in_subtree())
        return sorted(result, key=lambda n: n.priority, reverse=True)

    def is_leaf(self) -> bool:
        """Check if this node is a leaf (has no children)."""
        return len(self.children) == 0

    def add_child(self, node: Node) -> None:
        """Add a child node."""
        node.parent_id = self.id
        self.children.append(node)
