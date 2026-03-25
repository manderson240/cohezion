"""
Search state management for GPU kernel optimization.

Tracks optimization progress, frontier, and best results.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class NodeStatus(Enum):
    OPEN = "open"  # Pending optimization hypothesis
    CLOSED = "closed"  # Visited with attached program
    PRUNED = "pruned"  # Removed from search


@dataclass
class SearchNode:
    """Represents a node in the optimization search tree."""

    node_id: str
    kernel_type: str  # "gemm", "moe", "mla"
    optimization_intent: str  # e.g., "8-wave ping-pong", "LDS swizzle"
    parent_program: str | None  # Path to parent HIP kernel
    priority_score: float = 0.5  # World model estimate [0,1]
    status: NodeStatus = NodeStatus.OPEN
    performance_latency: float | None = None  # µs (if CLOSED)
    performance_geomean: float | None = None
    correctness_pass: bool | None = None
    children: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchNode:
        data["status"] = NodeStatus(data["status"])
        return cls(**data)


@dataclass
class EvalResult:
    """Result from kernel evaluation (compile + benchmark)."""

    success: bool
    latency_us: float | None = None
    geomean_us: float | None = None
    correctness_pass: bool | None = None
    error_msg: str | None = None
    compile_log: str | None = None
    benchmark_log: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchState:
    """Maintains the complete search tree state."""

    nodes: dict[str, SearchNode] = field(default_factory=dict)
    frontier: list[str] = field(default_factory=list)  # Open node IDs
    best_kernel: str | None = None
    best_latency: float | None = None
    total_evaluations: int = 0
    budget_remaining: int = 120

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "frontier": self.frontier,
            "best_kernel": self.best_kernel,
            "best_latency": self.best_latency,
            "total_evaluations": self.total_evaluations,
            "budget_remaining": self.budget_remaining,
        }

    def save(self, path: Path) -> None:
        """Persist search state to JSON."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> SearchState:
        """Load search state from JSON."""
        with open(path) as f:
            data = json.load(f)

        state = cls()
        state.frontier = data["frontier"]
        state.best_kernel = data["best_kernel"]
        state.best_latency = data["best_latency"]
        state.total_evaluations = data["total_evaluations"]
        state.budget_remaining = data["budget_remaining"]

        for node_id, node_data in data["nodes"].items():
            state.nodes[node_id] = SearchNode.from_dict(node_data)

        return state


class SearchTree:
    """
    Manages the optimization search tree for GPU kernels.

    Implements iterative optimization:
    1. Action Selection: Pick highest-priority from frontier
    2. Program Instantiation: Generate HIP kernel (stagnation tolerance)
    3. World Model Update: Insert/Update/Prune based on feedback
    """

    def __init__(self, save_path: Path = Path("optimizer/search_state.json")):
        self.save_path = save_path
        self.state = SearchState()

        if save_path.exists():
            self.state = SearchState.load(save_path)
            print(f"Loaded search state from {save_path}")
            print(f"  Nodes: {len(self.state.nodes)}")
            print(f"  Frontier: {len(self.state.frontier)} open")
            print(f"  Best latency: {self.state.best_latency} µs")

    def add_node(self, node: SearchNode) -> str:
        """Add node to search tree."""
        self.state.nodes[node.node_id] = node
        if node.status == NodeStatus.OPEN:
            self.state.frontier.append(node.node_id)

        self._autosave()
        return node.node_id

    def select_action(self) -> SearchNode | None:
        """
        Select highest-priority action from frontier.

        Returns:
            SearchNode with highest priority_score, or None if frontier empty
        """
        if not self.state.frontier:
            return None

        # Sort by priority (descending)
        frontier_nodes = [self.state.nodes[node_id] for node_id in self.state.frontier]
        frontier_nodes.sort(key=lambda n: n.priority_score, reverse=True)

        return frontier_nodes[0]

    def close_node(
        self,
        node_id: str,
        program_path: str,
        result: EvalResult,
    ) -> None:
        """
        Mark node as CLOSED with performance data.

        Updates best_kernel if this is the fastest so far.
        """
        node = self.state.nodes[node_id]
        node.status = NodeStatus.CLOSED
        node.performance_latency = result.latency_us
        node.performance_geomean = result.geomean_us
        node.correctness_pass = result.correctness_pass
        node.updated_at = time.time()

        # Update best if faster
        if result.success and result.latency_us:
            if self.state.best_latency is None or result.latency_us < self.state.best_latency:
                self.state.best_kernel = program_path
                self.state.best_latency = result.latency_us

        # Remove from frontier
        if node_id in self.state.frontier:
            self.state.frontier.remove(node_id)

        self.state.total_evaluations += 1
        self.state.budget_remaining -= 1

        self._autosave()

    def prune_node(self, node_id: str) -> None:
        """Mark node as PRUNED (remove from search)."""
        node = self.state.nodes[node_id]
        node.status = NodeStatus.PRUNED
        node.updated_at = time.time()

        if node_id in self.state.frontier:
            self.state.frontier.remove(node_id)

        self._autosave()

    def insert_child(
        self,
        parent_id: str,
        intent: str,
        priority: float = 0.5,
    ) -> str:
        """
        Insert child node with new optimization intent.

        Called by world model after analyzing execution feedback.
        """
        parent = self.state.nodes[parent_id]

        child_id = f"{parent_id}_child_{len(parent.children) + 1}"
        child = SearchNode(
            node_id=child_id,
            kernel_type=parent.kernel_type,
            optimization_intent=intent,
            parent_program=parent.parent_program,
            priority_score=priority,
        )

        parent.children.append(child_id)
        self.add_node(child)

        return child_id

    def update_priority(self, node_id: str, new_priority: float) -> None:
        """Update node priority score based on new evidence."""
        node = self.state.nodes[node_id]
        node.priority_score = new_priority
        node.updated_at = time.time()

        self._autosave()

    def _autosave(self) -> None:
        """Auto-save search state."""
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.state.save(self.save_path)

    def __repr__(self) -> str:
        return (
            f"SearchTree(nodes={len(self.state.nodes)}, "
            f"frontier={len(self.state.frontier)}, "
            f"best={self.state.best_latency}µs, "
            f"budget={self.state.budget_remaining})"
        )


def init_search_tree() -> SearchTree:
    """
    Initialize search tree with initial optimization hypotheses.

    Call this at the start of an optimization campaign.
    """
    tree = SearchTree()

    # Initial frontier for GEMM kernel
    initial_intents = [
        ("kernel_v1", "Fused quant+GEMM (single kernel)", 0.9),
        ("kernel_v2", "8-wave ping-pong scheduling", 0.8),
        ("kernel_v3", "LDS swizzle XOR remap", 0.75),
        ("kernel_v4", "Direct global→LDS 128-bit", 0.7),
        ("kernel_v5", "MFMA tile tuning", 0.65),
    ]

    for node_id, intent, priority in initial_intents:
        node = SearchNode(
            node_id=node_id,
            kernel_type="gemm",
            optimization_intent=intent,
            parent_program="kernels/mxfp4-mm/kernel_v1.hip",
            priority_score=priority,
        )
        tree.add_node(node)

    print(f"Initialized search tree with {len(initial_intents)} hypotheses")
    return tree


if __name__ == "__main__":
    # Demo: Initialize and inspect search tree
    tree = init_search_tree()
    print(tree)
    print("\nFrontier:")
    for node_id in tree.state.frontier:
        node = tree.state.nodes[node_id]
        print(f"  {node.node_id}: {node.optimization_intent} (p={node.priority_score})")
