"""K-Search tree module for managing kernel optimization search trees."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .node import Node


class KernelTree:
    """Represents a kernel optimization search tree.

    Attributes:
        version: Tree format version
        kernel: Kernel type (gemm, moe, mla)
        hardware: Target hardware platform
        root: Root node of the tree
        metadata: Tree-level metadata
    """

    def __init__(
        self,
        version: str = "2.0.0",
        kernel: str = "",
        hardware: str = "MI355X",
        root: Node | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.version = version
        self.kernel = kernel
        self.hardware = hardware
        self.root = root or Node(id=f"{kernel}_root_001", name=f"{kernel}_baseline")
        self.metadata = metadata or {
            "total_nodes": 1,
            "open_nodes": 1,
            "closed_nodes": 0,
            "pruned_nodes": 0,
            "stagnation_limit": 7,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KernelTree:
        """Create a KernelTree from a dictionary."""
        root_data = data.get("root", {})
        root = Node.from_dict(root_data) if isinstance(root_data, dict) else Node()

        return cls(
            version=data.get("version", "2.0.0"),
            kernel=data.get("kernel", ""),
            hardware=data.get("hardware", "MI355X"),
            root=root,
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the KernelTree to a dictionary."""
        return {
            "version": self.version,
            "kernel": self.kernel,
            "hardware": self.hardware,
            "created": self.metadata.get("last_updated", ""),
            "root": self.root.to_dict(),
            "metadata": self.metadata,
        }

    def count_nodes(self) -> int:
        """Count total nodes in the tree."""
        return self.root.count_subtree()

    def count_by_status(self, status: str) -> int:
        """Count nodes with a specific status."""
        return self.root.count_by_status(status)

    def find_node(self, node_id: str) -> Node | None:
        """Find a node by ID in the tree."""
        return self.root.find_in_subtree(node_id)

    def get_open_nodes(self) -> list[Node]:
        """Get all nodes with OPEN status, sorted by priority."""
        return self.root.get_open_in_subtree()


def load_tree(path: str | Path) -> KernelTree:
    """Load a kernel tree from a JSON file.

    Args:
        path: Path to the JSON file

    Returns:
        Loaded KernelTree instance
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return KernelTree.from_dict(data)


def save_tree(tree: KernelTree, path: str | Path) -> None:
    """Save a kernel tree to a JSON file.

    Args:
        tree: KernelTree to save
        path: Path to save the JSON file
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tree.to_dict(), f, indent=2)
