"""K-Search tree for adaptive kernel optimization strategy exploration."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class NodeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    DIVERGED = "DIVERGED"


KERNEL_BASE_K: dict[str, int] = {
    "mla": 12,
    "moe": 8,
    "gemm": 7,
}

MIN_K = 3


@dataclass
class KNode:
    id: str
    parent_id: str | None
    strategy: str
    status: NodeStatus
    v_score: float
    depth: int
    attempt_history: list[dict[str, Any]] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    kernel_type: str = "gemm"
    meta_prompt: str | None = None

    @property
    def best_score(self) -> float:
        if not self.attempt_history:
            return 0.0
        return max(a["score"] for a in self.attempt_history)

    @property
    def success_rate(self) -> float:
        """Fraction of attempts with score > 0.5."""
        if not self.attempt_history:
            return 0.0
        successes = sum(1 for a in self.attempt_history if a["score"] > 0.5)
        return successes / len(self.attempt_history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "strategy": self.strategy,
            "status": self.status.value,
            "v_score": self.v_score,
            "depth": self.depth,
            "attempt_history": self.attempt_history,
            "children": self.children,
            "kernel_type": self.kernel_type,
            "meta_prompt": self.meta_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KNode:
        return cls(
            id=data["id"],
            parent_id=data.get("parent_id"),
            strategy=data["strategy"],
            status=NodeStatus(data["status"]),
            v_score=data["v_score"],
            depth=data["depth"],
            attempt_history=data.get("attempt_history", []),
            children=data.get("children", []),
            kernel_type=data.get("kernel_type", "gemm"),
            meta_prompt=data.get("meta_prompt"),
        )


class KSearchTree:

    def __init__(self, kernel_type: str) -> None:
        if kernel_type not in KERNEL_BASE_K:
            raise ValueError(
                f"kernel_type must be one of {list(KERNEL_BASE_K)}, got {kernel_type!r}"
            )
        self.kernel_type = kernel_type
        self.nodes: dict[str, KNode] = {}

    def _gen_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def insert_child(
        self,
        parent_id: str | None,
        strategy: str,
        v_score: float,
        meta_prompt: str | None = None,
    ) -> KNode:
        """Add a child node under *parent_id* (None for root-level nodes)."""
        depth = 0
        if parent_id is not None:
            parent = self.nodes.get(parent_id)
            if parent is None:
                raise KeyError(f"Parent node {parent_id!r} not found")
            depth = parent.depth + 1

        node = KNode(
            id=self._gen_id(),
            parent_id=parent_id,
            strategy=strategy,
            status=NodeStatus.OPEN,
            v_score=max(0.0, min(1.0, v_score)),
            depth=depth,
            kernel_type=self.kernel_type,
            meta_prompt=meta_prompt,
        )
        self.nodes[node.id] = node

        if parent_id is not None:
            self.nodes[parent_id].children.append(node.id)

        return node

    def select_best(self) -> KNode:
        """Return the highest V-score OPEN frontier node.

        Raises ValueError when no OPEN nodes exist.
        """
        open_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.OPEN]
        if not open_nodes:
            raise ValueError("No OPEN nodes in tree")
        return max(open_nodes, key=lambda n: n.v_score)
    _STAGNATION_WINDOW = 5
    _STAGNATION_DELTA = 0.02

    def record_attempt(self, node_id: str, code: str, score: float) -> None:
        """Append an attempt and check for stagnation."""
        node = self.nodes[node_id]
        node.attempt_history.append(
            {
                "code": code,
                "score": score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        node.v_score = max(node.v_score, score)

        # Stagnation: last N attempts show no meaningful improvement
        recent = node.attempt_history[-self._STAGNATION_WINDOW :]
        if len(recent) >= self._STAGNATION_WINDOW:
            scores = [a["score"] for a in recent]
            if max(scores) - min(scores) < self._STAGNATION_DELTA:
                self.prune_node(node_id)

    def adaptive_k(self, node: KNode) -> int:
        """Compute branching factor K for *node*.

        K = base(kernel) - depth + parent_bonus, clamped to [MIN_K, base].
        """
        base = KERNEL_BASE_K[self.kernel_type]
        k = base - node.depth

        # Parent success bonus
        if node.parent_id is not None:
            parent = self.nodes.get(node.parent_id)
            if parent is not None and parent.success_rate > 0.5:
                k += 2

        return max(MIN_K, min(k, base + 2))

    def check_divergence(self, node: KNode, score: float) -> bool:
        """True when *score* is significantly worse than the node's best."""
        best = node.best_score
        if best == 0.0:
            return False
        return score < 0.8 * best

    def apply_evolution(self, results: list[dict[str, Any]]) -> None:
        """Process a batch of evolution operations.

        Each result dict must have an ``"op"`` key:
        - ``INSERT``: requires ``parent_id``, ``strategy``, ``v_score``
        - ``UPDATE``: requires ``node_id``, ``code``, ``score``
        - ``PRUNE``:  requires ``node_id``
        """
        for r in results:
            op = r["op"]
            if op == "INSERT":
                self.insert_child(r["parent_id"], r["strategy"], r["v_score"])
            elif op == "UPDATE":
                self.record_attempt(r["node_id"], r["code"], r["score"])
            elif op == "PRUNE":
                self.prune_node(r["node_id"])
            else:
                raise ValueError(f"Unknown evolution op: {op!r}")

    def prune_node(self, node_id: str) -> None:
        """Mark a node CLOSED (exhausted, stagnant)."""
        self.nodes[node_id].status = NodeStatus.CLOSED

    def diverge_node(self, node_id: str) -> None:
        """Mark a node DIVERGED for cross-kernel learning."""
        self.nodes[node_id].status = NodeStatus.DIVERGED

    def get_cross_kernel_failures(self) -> list[str]:
        """Return strategies of DIVERGED nodes (share with other kernels)."""
        return [
            n.strategy
            for n in self.nodes.values()
            if n.status == NodeStatus.DIVERGED
        ]

    def get_cross_kernel_successes(self) -> list[dict[str, Any]]:
        """Return strategies whose best score exceeds 0.8."""
        out: list[dict[str, Any]] = []
        for n in self.nodes.values():
            if n.best_score > 0.8:
                out.append(
                    {
                        "strategy": n.strategy,
                        "best_score": n.best_score,
                        "kernel_type": n.kernel_type,
                        "depth": n.depth,
                    }
                )
        return out

    def save(self, path: str | Path) -> None:
        """Persist tree to JSON."""
        payload = {
            "kernel_type": self.kernel_type,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> KSearchTree:
        """Restore tree from JSON."""
        data = json.loads(Path(path).read_text())
        tree = cls(kernel_type=data["kernel_type"])
        for nid, ndata in data["nodes"].items():
            tree.nodes[nid] = KNode.from_dict(ndata)
        return tree

    def summary(self) -> str:
        open_ct = sum(1 for n in self.nodes.values() if n.status == NodeStatus.OPEN)
        closed_ct = sum(1 for n in self.nodes.values() if n.status == NodeStatus.CLOSED)
        div_ct = sum(1 for n in self.nodes.values() if n.status == NodeStatus.DIVERGED)
        lines = [
            f"KSearchTree(kernel={self.kernel_type}, nodes={len(self.nodes)}, "
            f"open={open_ct}, closed={closed_ct}, diverged={div_ct})",
        ]
        for n in self.nodes.values():
            indent = "  " * n.depth
            lines.append(
                f"  {indent}[{n.status.value:>8}] {n.strategy}  "
                f"v={n.v_score:.3f}  attempts={len(n.attempt_history)}  "
                f"K={self.adaptive_k(n)}"
            )
        return "\n".join(lines)

if __name__ == "__main__":
    tree = KSearchTree("moe")

    # Root-level strategies
    a = tree.insert_child(None, "split_experts_v1", 0.65)
    b = tree.insert_child(None, "fused_gate_topk", 0.72)
    c = tree.insert_child(None, "shared_expert_reuse", 0.58)

    # Record some attempts
    tree.record_attempt(a.id, "# split impl v1\n...", 0.67)
    tree.record_attempt(b.id, "# fused gate v1\n...", 0.74)
    tree.record_attempt(b.id, "# fused gate v2\n...", 0.81)
    tree.record_attempt(c.id, "# shared reuse v1\n...", 0.60)
    tree.record_attempt(c.id, "# shared reuse v2\n...", 0.35)

    # Divergence: c's latest score dropped well below its best (0.35 < 0.8 * 0.60)
    if tree.check_divergence(c, 0.35):
        tree.diverge_node(c.id)

    # Expand best node
    best = tree.select_best()
    k = tree.adaptive_k(best)
    tree.insert_child(best.id, f"{best.strategy}__refine_tiling", 0.78)
    tree.insert_child(best.id, f"{best.strategy}__warp_shuffle", 0.75)

    print(tree.summary())
    print()
    print(f"Adaptive K for best node ({best.strategy}): {k}")
    print(f"Cross-kernel failures: {tree.get_cross_kernel_failures()}")
    print(f"Cross-kernel successes: {tree.get_cross_kernel_successes()}")
