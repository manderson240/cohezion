"""K-Search tree for kernel optimization.

Tree-structured search over kernel parameter configurations.
Each node is a strategy (e.g., "KSPLIT=4 for shape X") with priority,
attempt tracking, stagnation-based pruning (K=7), and trajectory history
for LLM world model co-evolution.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


log = logging.getLogger("ksearch_tree")

STAGNATION_THRESHOLD = 7  # Prune after 7 attempts without improvement


@dataclass
class AttemptRecord:
    """Single attempt on a node — used for trajectory tracking."""

    result_us: float
    parameters: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    source: str = "template"  # "template" or "llm"


@dataclass
class KNode:
    id: str
    strategy: str
    parameters: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    priority: float = 0.5  # 0.0 (low) to 1.0 (high)
    attempts: int = 0
    best_result_us: float | None = None
    stagnation_count: int = 0
    status: str = "active"  # active | exhausted | pruned
    children: list[str] = field(default_factory=list)
    notes: str = ""
    attempt_history: list[dict[str, Any]] = field(default_factory=list)

    def is_selectable(self) -> bool:
        return self.status == "active"

    def record_attempt(
        self,
        result_us: float,
        parameters: dict[str, Any] | None = None,
        source: str = "template",
    ) -> None:
        """Record a single attempt for trajectory tracking."""
        from datetime import datetime

        self.attempt_history.append(
            {
                "result_us": result_us,
                "parameters": parameters or self.parameters,
                "timestamp": datetime.now().isoformat(),
                "source": source,
            }
        )

    def get_trajectory_summary(self) -> str:
        """Compact trajectory for LLM prompts."""
        if not self.attempt_history:
            return "No attempts yet"
        results = [a["result_us"] for a in self.attempt_history]
        sources = [a.get("source", "template") for a in self.attempt_history]
        llm_count = sources.count("llm")
        return (
            f"{len(results)} attempts: "
            f"min={min(results):.1f}µs, max={max(results):.1f}µs, "
            f"last={results[-1]:.1f}µs, "
            f"llm_generated={llm_count}/{len(results)}"
        )


class KSearchTree:
    """K-Search optimization tree with SELECT/INSERT/UPDATE/PRUNE."""

    def __init__(self, kernel_name: str):
        self.kernel_name = kernel_name
        self.nodes: dict[str, KNode] = {}
        self.root_id: str | None = None

    def insert_root(self, strategy: str, parameters: dict | None = None) -> KNode:
        node = KNode(
            id=f"root_{self.kernel_name}",
            strategy=strategy,
            parameters=parameters or {},
            priority=1.0,
        )
        self.nodes[node.id] = node
        self.root_id = node.id
        return node

    def insert_child(
        self,
        parent_id: str,
        strategy: str,
        parameters: dict[str, Any],
        priority: float = 0.5,
        notes: str = "",
    ) -> KNode:
        if parent_id not in self.nodes:
            raise KeyError(f"Parent {parent_id} not found")
        node_id = f"n_{uuid.uuid4().hex[:8]}"
        node = KNode(
            id=node_id,
            strategy=strategy,
            parameters=parameters,
            parent_id=parent_id,
            priority=priority,
            notes=notes,
        )
        self.nodes[node_id] = node
        self.nodes[parent_id].children.append(node_id)
        return node

    def select_best(self) -> KNode | None:
        """Select highest-priority active node (leaf-first, then internal)."""
        active = [n for n in self.nodes.values() if n.is_selectable()]
        if not active:
            return None
        # Prefer leaves (no active children) over internal nodes
        _dummy = KNode(id="", strategy="", status="pruned")
        leaves = [
            n
            for n in active
            if not any(self.nodes.get(c, _dummy).is_selectable() for c in n.children)
        ]
        candidates = leaves if leaves else active
        return max(candidates, key=lambda n: n.priority)

    def update_result(self, node_id: str, result_us: float) -> None:
        """Update node with benchmark result. Tracks improvement/stagnation."""
        node = self.nodes[node_id]
        node.attempts += 1

        if node.best_result_us is None or result_us < node.best_result_us:
            improvement = (
                (node.best_result_us - result_us) / node.best_result_us
                if node.best_result_us
                else 1.0
            )
            node.best_result_us = result_us
            node.stagnation_count = 0
            # Boost priority on improvement
            node.priority = min(1.0, node.priority + 0.1 * improvement)
        else:
            node.stagnation_count += 1

        # Auto-prune on stagnation
        if node.stagnation_count >= STAGNATION_THRESHOLD:
            node.status = "exhausted"
            node.notes += f" [Exhausted after {node.attempts} attempts]"

    def mark_failed(self, node_id: str, reason: str) -> None:
        """Mark node as pruned due to failure (correctness, crash, etc.)."""
        node = self.nodes[node_id]
        node.status = "pruned"
        node.notes += f" [PRUNED: {reason}]"

    def decay_priorities(self, factor: float = 0.95) -> None:
        """Decay all active node priorities to encourage exploration."""
        for node in self.nodes.values():
            if node.is_selectable():
                node.priority *= factor

    def get_stats(self) -> dict[str, Any]:
        """Summary statistics for the tree."""
        active = [n for n in self.nodes.values() if n.status == "active"]
        exhausted = [n for n in self.nodes.values() if n.status == "exhausted"]
        pruned = [n for n in self.nodes.values() if n.status == "pruned"]
        best = min(
            (n for n in self.nodes.values() if n.best_result_us is not None),
            key=lambda n: n.best_result_us,  # type: ignore[arg-type]
            default=None,
        )
        return {
            "kernel": self.kernel_name,
            "total_nodes": len(self.nodes),
            "active": len(active),
            "exhausted": len(exhausted),
            "pruned": len(pruned),
            "best_us": best.best_result_us if best else None,
            "best_strategy": best.strategy if best else None,
            "total_attempts": sum(n.attempts for n in self.nodes.values()),
        }

    # --- World Model Evolution (K-Search pi_plan) ---

    def get_trajectory(self, node_id: str) -> list[dict[str, Any]]:
        """Get full attempt history for a node and its ancestors."""
        trajectory: list[dict[str, Any]] = []
        current_id: str | None = node_id
        while current_id and current_id in self.nodes:
            node = self.nodes[current_id]
            trajectory.append(
                {
                    "node_id": node.id,
                    "strategy": node.strategy,
                    "attempts": node.attempts,
                    "best_us": node.best_result_us,
                    "status": node.status,
                    "history": node.attempt_history[-5:],  # Last 5 for brevity
                }
            )
            current_id = node.parent_id
        trajectory.reverse()  # Root first
        return trajectory

    def to_summary(self, max_nodes: int = 20) -> str:
        """Compact tree summary for LLM prompts (token-efficient)."""
        lines = [f"K-Search Tree: {self.kernel_name}"]
        stats = self.get_stats()
        lines.append(
            f"  {stats['total_nodes']} nodes "
            f"({stats['active']} active, {stats['exhausted']} exhausted, "
            f"{stats['pruned']} pruned), "
            f"best={stats['best_us']}µs"
        )
        # Show nodes sorted by priority (most promising first)
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda n: (n.status != "active", -n.priority),
        )
        for node in sorted_nodes[:max_nodes]:
            depth = self._depth(node.id)
            indent = "  " * (depth + 1)
            result = f"{node.best_result_us:.1f}µs" if node.best_result_us else "untested"
            lines.append(
                f"{indent}[{node.status[0].upper()}] {node.strategy} "
                f"(p={node.priority:.2f}, {result}, "
                f"{node.attempts} attempts)"
            )
        return "\n".join(lines)

    def _depth(self, node_id: str) -> int:
        """Compute depth of a node in the tree."""
        depth = 0
        current = node_id
        while current in self.nodes and self.nodes[current].parent_id:
            current = self.nodes[current].parent_id  # type: ignore[assignment]
            depth += 1
        return depth

    def apply_evolution(self, evolution: dict[str, Any]) -> dict[str, int]:
        """Atomically apply INSERT/UPDATE/PRUNE from LLM world model.

        Args:
            evolution: {"insert": [...], "update": {...}, "prune": [...]}

        Returns:
            Counts: {"inserted": N, "updated": N, "pruned": N}
        """
        counts = {"inserted": 0, "updated": 0, "pruned": 0}

        # INSERT new child nodes
        for child in evolution.get("insert", []):
            parent_id = child.get("parent_id", self.root_id)
            if parent_id and parent_id in self.nodes:
                strategy = child.get("strategy", "")
                if not strategy:
                    continue
                priority = float(child.get("priority", 0.6))
                params = child.get("parameters", {})
                try:
                    self.insert_child(
                        parent_id=parent_id,
                        strategy=strategy,
                        parameters=params,
                        priority=min(1.0, max(0.0, priority)),
                        notes="[LLM-proposed]",
                    )
                    counts["inserted"] += 1
                    log.info(f"LLM INSERT: '{strategy}' under {parent_id}")
                except (KeyError, ValueError) as e:
                    log.warning(f"LLM INSERT failed: {e}")

        # UPDATE V-scores (priorities)
        for node_id, new_priority in evolution.get("update", {}).items():
            if node_id in self.nodes:
                node = self.nodes[node_id]
                old_p = node.priority
                node.priority = min(1.0, max(0.0, float(new_priority)))
                counts["updated"] += 1
                log.info(f"LLM UPDATE: {node_id} priority {old_p:.2f} → {node.priority:.2f}")

        # PRUNE branches
        for node_id in evolution.get("prune", []):
            if node_id in self.nodes and self.nodes[node_id].status == "active":
                self.strategic_prune(node_id, reason="LLM world model")
                counts["pruned"] += 1

        return counts

    def strategic_prune(self, node_id: str, reason: str = "") -> None:
        """Prune a node and all its active descendants."""
        if node_id not in self.nodes:
            return
        node = self.nodes[node_id]
        node.status = "pruned"
        node.notes += f" [STRATEGIC PRUNE: {reason}]"
        log.info(f"PRUNE: {node_id} ({node.strategy}) — {reason}")
        # Recursively prune children
        for child_id in node.children:
            if child_id in self.nodes and self.nodes[child_id].status == "active":
                self.strategic_prune(child_id, reason=f"parent {node_id} pruned")

    def update_v_scores(self, scores: dict[str, float]) -> None:
        """Bulk update node priorities (V-scores) from LLM assessment."""
        for node_id, score in scores.items():
            if node_id in self.nodes:
                self.nodes[node_id].priority = min(1.0, max(0.0, score))

    # --- Persistence ---

    def save(self, path: Path) -> None:
        data = {
            "kernel_name": self.kernel_name,
            "root_id": self.root_id,
            "nodes": {nid: asdict(n) for nid, n in self.nodes.items()},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to tmp, then rename (prevents corruption on crash)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.rename(path)

    @classmethod
    def load(cls, path: Path) -> KSearchTree:
        data = json.loads(path.read_text())
        tree = cls(data["kernel_name"])
        tree.root_id = data["root_id"]
        for nid, ndata in data["nodes"].items():
            tree.nodes[nid] = KNode(**ndata)
        return tree

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"KSearchTree({self.kernel_name}: "
            f"{stats['active']} active, {stats['total_attempts']} attempts, "
            f"best={stats['best_us']}µs)"
        )
